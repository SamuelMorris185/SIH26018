import io
import re
import uuid
import anyio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image, ImageEnhance, ImageFilter

from app.core.logging import logger
from app.core.config import settings
from app.core.exceptions import (
    ExtractionProcessingError,
    OCREngineUnavailableError,
)
from app.schemas.extraction import (
    RawExtractionPayload,
    FieldExtractionEvidence,
    ConfidenceCategory,
    categorize_confidence,
)
from app.services.extraction.provider import BaseExtractionProvider
from app.services.normalization_service import NormalizationService

class TesseractOCRProvider(BaseExtractionProvider):
    """
    Production-grade local OCR extraction provider utilizing the Tesseract OCR engine
    (via pytesseract) and pypdf for digital and scanned land records.
    Features automated image preprocessing (grayscale, contrast, rescaling, sharpening),
    resilient multi-page/raster PDF extraction, and comprehensive Indian revenue terminology parsing.
    Operates offline without external cloud dependencies.
    """

    def __init__(self, tesseract_cmd: Optional[str] = None):
        self.cmd_path = tesseract_cmd or settings.TESSERACT_CMD_PATH
        self._init_pytesseract()

    def _init_pytesseract(self) -> None:
        try:
            import pytesseract
            import shutil
            if self.cmd_path:
                pytesseract.pytesseract.tesseract_cmd = self.cmd_path
            else:
                detected = shutil.which("tesseract") or "tesseract"
                pytesseract.pytesseract.tesseract_cmd = detected
        except ImportError:
            pass

    @property
    def provider_name(self) -> str:
        return "TESSERACT_OCR_V1"

    @property
    def is_available(self) -> bool:
        """Verifies if pytesseract is installed and the tesseract binary is responsive."""
        try:
            import pytesseract
            if self.cmd_path:
                pytesseract.pytesseract.tesseract_cmd = self.cmd_path
            version = pytesseract.get_tesseract_version()
            return bool(version)
        except Exception as exc:
            logger.debug(f"[TESSERACT_OCR] Availability check failed: {exc}")
            return False

    def get_engine_status(self) -> Dict[str, Any]:
        """Returns non-sensitive health and diagnostic info regarding the Tesseract OCR engine."""
        try:
            import pytesseract
            if self.cmd_path:
                pytesseract.pytesseract.tesseract_cmd = self.cmd_path
            version_str = str(pytesseract.get_tesseract_version())
            languages = pytesseract.get_languages()
            return {
                "engine": self.provider_name,
                "available": True,
                "version": version_str,
                "supported_languages": sorted(languages) if languages else ["eng"],
            }
        except Exception as exc:
            return {
                "engine": self.provider_name,
                "available": False,
                "version": None,
                "supported_languages": [],
                "error": str(exc)
            }

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Applies computer vision preprocessing to maximize Tesseract character recognition:
        1. Converts to single-channel Grayscale ('L').
        2. Auto-upscales low-resolution scans (< 1200px width) using Lanczos interpolation.
        3. Enhances contrast to sharpen text edges against aged paper/backgrounds.
        4. Applies a sharpening filter to reduce scanner/blur artifacts.
        """
        # Step 1: Grayscale conversion
        if image.mode != "L":
            gray = image.convert("L")
        else:
            gray = image.copy()

        # Step 2: Adaptive Rescaling for small scans
        w, h = gray.size
        if w < 1200:
            scale_factor = min(2.0, 1600.0 / max(1, w))
            new_w = int(w * scale_factor)
            new_h = int(h * scale_factor)
            gray = gray.resize((new_w, new_h), resample=Image.Resampling.LANCZOS)

        # Step 3: Contrast Enhancement
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(1.8)

        # Step 4: Sharpening
        sharpened = enhanced.filter(ImageFilter.SHARPEN)
        return sharpened

    async def extract_document_fields(
        self,
        document_id: uuid.UUID,
        file_bytes: bytes,
        file_name: str,
        mime_type: str
    ) -> RawExtractionPayload:
        return await anyio.to_thread.run_sync(
            self._extract_document_fields, document_id, file_bytes, file_name, mime_type
        )

    def _extract_document_fields(self, document_id, file_bytes, file_name, mime_type) -> RawExtractionPayload:
        logger.info(f"[TESSERACT_OCR] Starting real OCR extraction for '{file_name}' (doc_id={document_id}, size={len(file_bytes)} bytes)")

        if not file_bytes or len(file_bytes) == 0:
            raise ExtractionProcessingError("Cannot extract fields from an empty (0 bytes) document.")

        # Check binary availability
        if not self.is_available:
            err_msg = (
                "Tesseract OCR executable not detected in system PATH or TESSERACT_CMD_PATH. "
                "Please install Tesseract OCR locally (e.g. via 'scoop install tesseract' or 'winget install UB-Mannheim.TesseractOCR') "
                "or configure OCR_ENGINE=MOCK in .env for development."
            )
            logger.error(f"[TESSERACT_OCR] Engine unavailable: {err_msg}")
            raise OCREngineUnavailableError(self.provider_name, err_msg)

        import pytesseract

        raw_text = ""
        word_confidences: List[float] = []

        try:
            # Route 1: PDF Document
            if mime_type == "application/pdf" or file_name.lower().endswith(".pdf"):
                raw_text, word_confidences = self._extract_pdf(file_bytes)
            # Route 2: Raster Image (PNG, JPEG, TIFF, BMP, WEBP)
            else:
                try:
                    orig_image = Image.open(io.BytesIO(file_bytes))
                except Exception as img_exc:
                    logger.error(f"[TESSERACT_OCR] Corrupt or unreadable image file '{file_name}': {img_exc}")
                    raise ExtractionProcessingError(f"Corrupt or unreadable image file: {str(img_exc)}")

                # Preprocess image for optimal character recognition
                preprocessed = self._preprocess_image(orig_image)
                raw_text = pytesseract.image_to_string(preprocessed, config="--oem 3 --psm 3")

                # Word-level OCR confidence extraction
                data = pytesseract.image_to_data(preprocessed, output_type=pytesseract.Output.DICT)
                for conf in data.get("conf", []):
                    try:
                        c_val = float(conf)
                        if c_val >= 0:  # -1 indicates non-word elements
                            word_confidences.append(c_val / 100.0)
                    except (ValueError, TypeError):
                        pass

        except ExtractionProcessingError:
            raise
        except Exception as exc:
            logger.error(f"[TESSERACT_OCR] Extraction execution error on '{file_name}': {str(exc)}", exc_info=True)
            raise ExtractionProcessingError(f"OCR execution failed: {str(exc)}")

        # Calculate average base OCR confidence
        if word_confidences:
            avg_conf = round(sum(word_confidences) / len(word_confidences), 2)
        else:
            avg_conf = 0.85 if len(raw_text.strip()) > 30 else 0.35

        # Parse structured land record fields from the extracted OCR text
        extracted_fields, field_confidences, structured_fields, low_conf_fields = self._parse_land_record_text(
            raw_text, avg_conf
        )

        overall_conf = max(0.0, min(1.0, float(avg_conf)))
        overall_category = categorize_confidence(
            overall_conf,
            settings.CONFIDENCE_THRESHOLD_HIGH,
            settings.CONFIDENCE_THRESHOLD_MEDIUM
        )

        return RawExtractionPayload(
            document_id=document_id,
            provider=self.provider_name,
            raw_text=raw_text,
            extracted_fields=extracted_fields,
            field_confidences=field_confidences,
            structured_fields=structured_fields,
            confidence_score=overall_conf,
            confidence_category=overall_category,
            low_confidence_fields=low_conf_fields,
            status="SUCCESS"
        )

    def _extract_pdf(self, file_bytes: bytes) -> Tuple[str, List[float]]:
        """
        Extracts text from PDF documents.
        Handles both digital PDFs (text streams via pypdf) and scanned/rasterized PDFs
        by extracting embedded images and running Tesseract OCR.
        """
        import pypdf
        import pytesseract

        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        except Exception as pdf_exc:
            raise ExtractionProcessingError(f"Failed to read PDF file: {str(pdf_exc)}")

        extracted_pages: List[str] = []
        confidences: List[float] = []

        for idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""

            # If digital text stream has meaningful content (> 15 chars)
            if len(page_text.strip()) > 15:
                extracted_pages.append(page_text)
                words = page_text.split()
                confidences.extend([0.95] * max(1, len(words)))
            else:
                # Scanned / Rasterized PDF page: inspect embedded images
                page_img_text = []
                try:
                    for img_file in page.images:
                        img = Image.open(io.BytesIO(img_file.data))
                        prep_img = self._preprocess_image(img)
                        ocr_txt = pytesseract.image_to_string(prep_img)
                        if ocr_txt.strip():
                            page_img_text.append(ocr_txt)
                            data = pytesseract.image_to_data(prep_img, output_type=pytesseract.Output.DICT)
                            for conf in data.get("conf", []):
                                try:
                                    c_val = float(conf)
                                    if c_val >= 0:
                                        confidences.append(c_val / 100.0)
                                except (ValueError, TypeError):
                                    pass
                except Exception as img_err:
                    logger.debug(f"[TESSERACT_OCR] Embedded page image extraction warning: {img_err}")

                if page_img_text:
                    extracted_pages.append("\n".join(page_img_text))
                elif page_text.strip():
                    extracted_pages.append(page_text)

        full_text = "\n".join(extracted_pages)
        if not confidences:
            confidences = [0.90] if len(full_text.strip()) > 30 else [0.30]

        return full_text, confidences

    def _parse_land_record_text(
        self,
        text: str,
        base_confidence: float
    ) -> Tuple[Dict[str, Any], Dict[str, float], Dict[str, FieldExtractionEvidence], List[str]]:
        """
        Regex and pattern recognition engine identifying canonical land record fields from OCR text.
        Tolerant of common Indian land & revenue terminology variations across states:
        - State / Rajya / Prant
        - District / Dist / Jila / Zilla
        - Tehsil / Taluk / Taluka / Mandal / Tahsil
        - Village / Mauza / Gram / Gaon
        - Khasra / Survey No / Survey Number / Gat No / Gat
        - Khata / Khatoni / Khatauni / Account No
        - Patta / Patta No
        - Area / Rakba / Extent / Land Area / Kshetrafal
        - Classification / Land Type / Kism / Varg
        - Owner / Name of Owner / Khatedar / Bhumiswami / Holder / Patta Dharak
        - Co-owners / Sah-Khatedar / Joint Holders
        - Registration No / Reg No / Dastavej No
        - Mutation No / Namantaran No / Dakhil Kharij
        - Document Date / Registration Date / Tarikh
        """
        patterns = {
            "state": r"(?i)(?:State|Rajya|Prant)\s*[:\-]?\s*([A-Za-z\s]+?)(?:\s*(?:District|Dist|Jila|Zilla|Tehsil|Village|\n|$))",
            "district": r"(?i)(?:District|Dist\.?|Jila|Zilla)\s*[:\-]?\s*([A-Za-z\s]+?)(?:\s*(?:Tehsil|Taluk|Taluka|Mandal|Village|Mauza|\n|$))",
            "tehsil": r"(?i)(?:Tehsil|Taluka|Taluk|Tahsil|Mandal)\s*[:\-]?\s*([A-Za-z\s]+?)(?:\s*(?:Village|Gram|Mauza|Gaon|\n|$))",
            "village": r"(?i)(?:Village|Mauza|Gram|Gaon)\s*[:\-]?\s*([A-Za-z\s]+?)(?:\s*(?:Khasra|Survey|Gat|Khata|Patta|\n|$))",
            "khasra_number": r"(?i)(?:Khasra|Survey|Gat)\s*(?:No\.?|Number)?\s*[:\-]?\s*([\d]+(?:\s*[\/\-]\s*[\w\d]+)?)",
            "khata_number": r"(?i)(?:Khatauni|Khatoni|Khata|Account)\s*(?:No\.?|Number)?\s*[:\-]?\s*([\w\d]+)",
            "area_in_hectares": r"(?i)(?:Land\s*Area|Kshetrafal|Area|Rakba|Extent)\s*[:\-]?\s*([\d\.]+(?:\s*(?:ha|hectares?|acres?|bigha))?)",
            "land_classification": r"(?i)(?:Land\s*Type|Classification|Kism|Varg)\s*[:\-]?\s*([A-Za-z\-]+)",
            "owner_name": r"(?i)(?:Name\s*of\s*Owner|Patta\s*Dharak|Bhumiswami|Khatedar|Holder|Owner|Name)\s*[:\-]?\s*([A-Za-z\s\.]+?)(?:\s*(?:S\/o|W\/o|D\/o|Co-owner|Sah-Khatedar|Khata|$|\n))",
            "co_owners": r"(?i)(?:Co\-owners?|Sah\-Khatedar|Joint\s*Holders?|Hissedar)\s*[:\-]?\s*([A-Za-z\s\,\.]+?)(?:\s*(?:Patta|Registration|Khasra|Area|$|\n))",
            "patta_number": r"(?i)(?:Patta)\s*(?:No\.?|Number)?\s*[:\-]?\s*([\w\d\-\/]+)",
            "registration_number": r"(?i)(?:Registration|Dastavej|Reg\.?)\s*(?:No\.?|Number)?\s*[:\-]?\s*([\w\d\-\/]+)",
            "mutation_number": r"(?i)(?:Mutation|Namantaran|Dakhil\s*Kharij)\s*(?:No\.?|Number)?\s*[:\-]?\s*([\w\d\-\/]+)",
            "document_date": r"(?i)(?:Date\s*of\s*Registration|Registration\s*Date|Document\s*Date|Tarikh|Date)\s*[:\-]?\s*([\d]{1,4}[\/\-\.][\d]{1,2}[\/\-\.][\d]{1,4})"
        }

        extracted_fields: Dict[str, Any] = {}
        field_confidences: Dict[str, float] = {}
        structured_fields: Dict[str, FieldExtractionEvidence] = {}
        low_confidence_fields: List[str] = []

        for field_name, regex in patterns.items():
            match = re.search(regex, text)
            if match:
                raw_val = match.group(1).strip()
                match_conf = min(1.0, round(base_confidence * 0.98, 2))
                evidence_str = match.group(0).strip()
            else:
                raw_val = ""
                match_conf = 0.0
                evidence_str = None

            extracted_fields[field_name] = raw_val
            field_confidences[field_name] = match_conf

            category = categorize_confidence(
                match_conf,
                settings.CONFIDENCE_THRESHOLD_HIGH,
                settings.CONFIDENCE_THRESHOLD_MEDIUM
            )
            if category == ConfidenceCategory.LOW:
                low_confidence_fields.append(field_name)

            # Compute canonical normalized value for dual-preservation
            norm_val: Optional[Any] = None
            if raw_val:
                if field_name in ("state", "district", "tehsil", "village"):
                    norm_val = NormalizationService.normalize_title(raw_val)
                elif field_name == "owner_name":
                    norm_val = NormalizationService.normalize_name(raw_val)
                elif field_name == "co_owners":
                    norm_val = NormalizationService.normalize_co_owners(raw_val)
                elif field_name == "khasra_number":
                    norm_val = NormalizationService.normalize_khasra(raw_val)
                elif field_name == "khata_number":
                    norm_val = NormalizationService.normalize_khata(raw_val)
                elif field_name == "area_in_hectares":
                    norm_val = NormalizationService.normalize_area(raw_val)
                elif field_name == "land_classification":
                    norm_val = NormalizationService.normalize_classification(raw_val)
                elif field_name in ("patta_number", "registration_number", "mutation_number"):
                    norm_val = NormalizationService.normalize_identifier(raw_val)
                elif field_name == "document_date":
                    norm_date = NormalizationService.normalize_date(raw_val)
                    norm_val = norm_date.strftime("%Y-%m-%d") if norm_date else None

            structured_fields[field_name] = FieldExtractionEvidence(
                field=field_name,
                value=raw_val,
                normalized_value=norm_val,
                confidence=match_conf,
                category=category,
                source="tesseract_ocr",
                evidence=evidence_str
            )

        # Detect area unit
        area_raw = extracted_fields.get("area_in_hectares", "")
        if "acre" in str(area_raw).lower():
            extracted_fields["area_unit"] = "acre"
        elif "bigha" in str(area_raw).lower():
            extracted_fields["area_unit"] = "bigha"
        else:
            extracted_fields["area_unit"] = "hectare"

        # Defaults for mandatory fields only when text was extracted but field was absent
        # Missing geography stays missing so mandatory-field validation can flag it.
        if not extracted_fields.get("land_classification") and len(text.strip()) > 20:
            extracted_fields["land_classification"] = "Agricultural"

        return extracted_fields, field_confidences, structured_fields, low_confidence_fields
