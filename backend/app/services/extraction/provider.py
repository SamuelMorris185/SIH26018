from abc import ABC, abstractmethod
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from app.core.logging import logger
from app.core.config import settings
from app.core.exceptions import ExtractionProcessingError
from app.schemas.extraction import (
    RawExtractionPayload,
    FieldExtractionEvidence,
    ConfidenceCategory,
    categorize_confidence,
)

class BaseExtractionProvider(ABC):
    """
    Abstract interface for document text/field extraction providers (e.g. Mock, Tesseract, AWS Textract).
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the unique identifier of the extraction provider."""
        pass

    @property
    def is_available(self) -> bool:
        """Returns True if the extraction engine is installed and ready to process documents."""
        return True

    @abstractmethod
    async def extract_document_fields(
        self,
        document_id: uuid.UUID,
        file_bytes: bytes,
        file_name: str,
        mime_type: str
    ) -> RawExtractionPayload:
        """
        Executes extraction against the document binary and returns raw structured fields.
        """
        pass

class MockExtractionProvider(BaseExtractionProvider):
    """
    Simulated extraction provider for SIH26018 development, testing, and demonstration.
    Explicitly flags extracted output as mock/simulated data.
    Validates confidence scores and handles empty, corrupt, or specific discrepancy test conditions.
    """

    @property
    def provider_name(self) -> str:
        return "MOCK_OCR_V1"

    async def extract_document_fields(
        self,
        document_id: uuid.UUID,
        file_bytes: bytes,
        file_name: str,
        mime_type: str
    ) -> RawExtractionPayload:
        logger.info(f"[MOCK_OCR] Simulating document field extraction for '{file_name}' (doc_id={document_id}, size={len(file_bytes)} bytes)")
        
        # 1. Reject empty files
        if not file_bytes or len(file_bytes) == 0:
            logger.warning(f"[MOCK_OCR] Attempted extraction on empty file '{file_name}'")
            raise ExtractionProcessingError("Cannot extract fields from an empty (0 bytes) document.")

        lower_name = file_name.lower()

        # 2. Simulated corrupt/unreadable failure trigger for negative testing
        if "corrupt" in lower_name or "unreadable" in lower_name:
            logger.warning(f"[MOCK_OCR] Simulated OCR engine failure on degraded scan '{file_name}'")
            raise ExtractionProcessingError(f"OCR engine could not decipher corrupted scan '{file_name}'.")

        # 3. Simulated discrepancy triggers for Phase 3/4 validation failure testing
        if "discrepancy" in lower_name or "flagged" in lower_name:
            raw_fields = {
                "state": "Madhya Pradesh",
                "district": "",  # Missing required field -> fails RequiredFieldsRule
                "tehsil": "Huzur",
                "village": "Bairagarh",
                "khasra_number": "104/??/2",  # Fails KhasraFormatRule
                "khata_number": "45",
                "area_in_hectares": "999.50 ha",  # Exceeds 500ha maximum -> fails AreaSanityRule
                "land_classification": "SpaceStation",  # Fails LandClassificationRule
                "owner_name": "Unverified Unknown Owner",
                "co_owners": [],
                "patta_number": "PATTA-ERR-00",
                "registration_number": "REG-INVALID",
                "mutation_number": "MUT-INVALID",
                "area_unit": "hectare",
                "document_type": "JAMABANDI"
            }
            field_confidences = {
                "state": 0.90, "district": 0.0, "tehsil": 0.85, "village": 0.88,
                "khasra_number": 0.40, "khata_number": 0.82, "area_in_hectares": 0.35, "land_classification": 0.50,
                "owner_name": 0.45, "registration_number": 0.30
            }
            overall_confidence = 0.55
        elif "owner_mismatch" in lower_name:
            # Same parcel (104/2, Bairagarh) but conflicting owner
            raw_fields = {
                "state": "Madhya Pradesh",
                "district": "Bhopal",
                "tehsil": "Huzur",
                "village": "Bairagarh",
                "khasra_number": "104/2",
                "khata_number": "45",
                "area_in_hectares": "1.2500 ha",
                "land_classification": "Agricultural",
                "owner_name": "Vikram Aditya Singh",  # Conflicting owner
                "co_owners": ["Rajesh Kumar"],
                "patta_number": "PATTA-2024-889",
                "registration_number": "REG-2024-MP-00999",
                "mutation_number": "MUT-2024-00888",
                "area_unit": "hectare",
                "document_type": "SALE_DEED"
            }
            field_confidences = {
                "state": 0.98, "district": 0.96, "tehsil": 0.94, "village": 0.95,
                "khasra_number": 0.93, "khata_number": 0.92, "area_in_hectares": 0.91,
                "land_classification": 0.95, "owner_name": 0.94
            }
            overall_confidence = 0.94
        elif "area_mismatch" in lower_name:
            # Same parcel (104/2, Bairagarh) but conflicting area
            raw_fields = {
                "state": "Madhya Pradesh",
                "district": "Bhopal",
                "tehsil": "Huzur",
                "village": "Bairagarh",
                "khasra_number": "104/2",
                "khata_number": "45",
                "area_in_hectares": "3.7500 ha",  # Discrepant area (> 0.01 ha difference)
                "land_classification": "Agricultural",
                "owner_name": "Ram Prasad Sharma",
                "co_owners": ["Shyam Prasad Sharma"],
                "patta_number": "PATTA-2024-889",
                "registration_number": "REG-2024-MP-00123",
                "mutation_number": "MUT-2024-00456",
                "area_unit": "hectare",
                "document_type": "JAMABANDI"
            }
            field_confidences = {
                "state": 0.97, "district": 0.95, "tehsil": 0.94, "village": 0.95,
                "khasra_number": 0.93, "khata_number": 0.92, "area_in_hectares": 0.88,
                "land_classification": 0.95, "owner_name": 0.96
            }
            overall_confidence = 0.94
        elif "low_confidence" in lower_name:
            # Mandatory fields have low confidence (< 0.60)
            raw_fields = {
                "state": "Madhya Pradesh",
                "district": "Bhopal",
                "tehsil": "Huzur",
                "village": "Bairagarh",
                "khasra_number": "104/2",
                "khata_number": "45",
                "area_in_hectares": "1.2500 ha",
                "land_classification": "Agricultural",
                "owner_name": "Ram Prasad Sharma",
                "co_owners": ["Shyam Prasad Sharma"],
                "patta_number": "PATTA-2024-889",
                "registration_number": "REG-2024-MP-00123",
                "mutation_number": "MUT-2024-00456",
                "area_unit": "hectare",
                "document_type": "JAMABANDI"
            }
            field_confidences = {
                "state": 0.95, "district": 0.90, "tehsil": 0.88, "village": 0.85,
                "khasra_number": 0.45,  # LOW confidence on mandatory khasra!
                "khata_number": 0.50,   # LOW confidence!
                "area_in_hectares": 0.52,  # LOW confidence!
                "land_classification": 0.90, "owner_name": 0.88
            }
            overall_confidence = 0.58
        elif "suspicious_date" in lower_name:
            # Mutation date prior to registration date
            raw_fields = {
                "state": "Madhya Pradesh",
                "district": "Bhopal",
                "tehsil": "Huzur",
                "village": "Bairagarh",
                "khasra_number": "104/2",
                "khata_number": "45",
                "area_in_hectares": "1.2500 ha",
                "land_classification": "Agricultural",
                "owner_name": "Ram Prasad Sharma",
                "co_owners": ["Shyam Prasad Sharma"],
                "patta_number": "PATTA-2024-889",
                "registration_number": "REG-2024-MP-00123",
                "mutation_number": "MUT-2024-00456",
                "document_date": "2024-05-10",
                "registration_date": "2024-06-01",
                "mutation_date": "2024-03-01",  # Suspicious: Mutation earlier than registration!
                "area_unit": "hectare",
                "document_type": "MUTATION_RECORD"
            }
            field_confidences = {
                "state": 0.98, "district": 0.95, "tehsil": 0.94, "village": 0.95,
                "khasra_number": 0.93, "khata_number": 0.92, "area_in_hectares": 0.90,
                "land_classification": 0.95, "owner_name": 0.96, "mutation_date": 0.91
            }
            overall_confidence = 0.94
        else:
            # Standard realistic extraction simulation
            raw_fields = {
                "state": "  Madhya Pradesh  ",
                "district": "bhopal",
                "tehsil": " Huzur ",
                "village": "Bairagarh",
                "khasra_number": " 104 / 2 ",
                "khata_number": "45",
                "area_in_hectares": "1.2500 ha",
                "land_classification": "agricultural",
                "owner_name": "Ram Prasad Sharma",
                "co_owners": ["Shyam Prasad Sharma"],
                "patta_number": "PATTA-2024-889",
                "registration_number": "REG-2024-MP-00123",
                "mutation_number": "MUT-2024-00456",
                "area_unit": "hectare",
                "document_type": "JAMABANDI",
                "document_date": "2024-01-15",
                "registration_date": "2024-01-20",
                "mutation_date": "2024-02-10",
                "source_document_reference": "Revenue Record Book Vol 4, Page 22"
            }
            field_confidences = {
                "state": 0.98, "district": 0.96, "tehsil": 0.93, "village": 0.95,
                "khasra_number": 0.91, "khata_number": 0.94, "area_in_hectares": 0.89,
                "land_classification": 0.92, "owner_name": 0.95, "co_owners": 0.90,
                "patta_number": 0.88, "registration_number": 0.92, "mutation_number": 0.89
            }
            overall_confidence = round(sum(field_confidences.values()) / len(field_confidences), 2)

        # 4. Strict confidence score bounds validation [0.0, 1.0]
        safe_confidence = max(0.0, min(1.0, float(overall_confidence)))
        overall_category = categorize_confidence(
            safe_confidence,
            settings.CONFIDENCE_THRESHOLD_HIGH,
            settings.CONFIDENCE_THRESHOLD_MEDIUM
        )

        # Build structured fields with evidence snippet and confidence categories
        structured_fields: Dict[str, FieldExtractionEvidence] = {}
        low_confidence_fields: List[str] = []

        for f_name, f_val in raw_fields.items():
            conf = field_confidences.get(f_name, safe_confidence)
            cat = categorize_confidence(
                conf,
                settings.CONFIDENCE_THRESHOLD_HIGH,
                settings.CONFIDENCE_THRESHOLD_MEDIUM
            )
            if cat == ConfidenceCategory.LOW:
                low_confidence_fields.append(f_name)

            evidence_snippet = f"{f_name.replace('_', ' ').title()}: {f_val}"
            structured_fields[f_name] = FieldExtractionEvidence(
                field=f_name,
                value=f_val,
                normalized_value=None,
                confidence=conf,
                category=cat,
                source="mock",
                evidence=evidence_snippet
            )

        simulated_raw_ocr_text = (
            "GOVERNMENT OF MADHYA PRADESH - REVENUE DEPARTMENT\n"
            "RECORD OF RIGHTS (JAMABANDI / KHASRA REGISTER)\n"
            f"District: {raw_fields.get('district', '')} | Tehsil: {raw_fields.get('tehsil', '')} | Village: {raw_fields.get('village', '')}\n"
            f"Khata Number: {raw_fields.get('khata_number', '')} | Khasra Number: {raw_fields.get('khasra_number', '')}\n"
            f"Owner Name: {raw_fields.get('owner_name', '')} | Co-Owners: {', '.join(raw_fields.get('co_owners', [])) if isinstance(raw_fields.get('co_owners'), list) else ''}\n"
            f"Area: {raw_fields.get('area_in_hectares', '')} | Classification: {raw_fields.get('land_classification', '')}\n"
            f"Registration No: {raw_fields.get('registration_number', '')} | Patta No: {raw_fields.get('patta_number', '')}\n"
            "Extracted via Mock OCR Engine v1.0.0 [SIMULATION]"
        )

        return RawExtractionPayload(
            document_id=document_id,
            provider=self.provider_name,
            raw_text=simulated_raw_ocr_text,
            extracted_fields=raw_fields,
            field_confidences=field_confidences,
            structured_fields=structured_fields,
            confidence_score=safe_confidence,
            confidence_category=overall_category,
            low_confidence_fields=low_confidence_fields,
            status="SUCCESS"
        )
