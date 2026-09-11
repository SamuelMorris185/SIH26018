import os
import uuid
import pytest
from PIL import Image

from app.core.exceptions import ExtractionProcessingError, OCREngineUnavailableError
from app.schemas.extraction import ConfidenceCategory
from app.services.extraction.tesseract_provider import TesseractOCRProvider
from tests.fixtures.sample_documents.manifest import get_fixture_bytes

@pytest.mark.asyncio
async def test_tesseract_provider_availability():
    provider = TesseractOCRProvider()
    assert provider.provider_name == "TESSERACT_OCR_V1"
    assert provider.is_available is True
    
    status_info = provider.get_engine_status()
    assert status_info["engine"] == "TESSERACT_OCR_V1"
    assert status_info["available"] is True
    assert status_info["version"] is not None
    assert "eng" in status_info["supported_languages"]

@pytest.mark.asyncio
async def test_tesseract_preprocessing():
    provider = TesseractOCRProvider()
    test_img = Image.new("RGB", (600, 400), color="blue")
    preprocessed = provider._preprocess_image(test_img)
    
    assert preprocessed.mode == "L"
    # Auto-upscaled because width was < 1200
    assert preprocessed.size[0] >= 1200

@pytest.mark.asyncio
async def test_tesseract_clean_image_extraction():
    provider = TesseractOCRProvider()
    image_bytes = get_fixture_bytes("clean_land_record.png")
    assert len(image_bytes) > 0, "clean_land_record.png fixture must exist"

    doc_id = uuid.uuid4()
    result = await provider.extract_document_fields(
        document_id=doc_id,
        file_bytes=image_bytes,
        file_name="clean_land_record.png",
        mime_type="image/png"
    )

    assert result.document_id == doc_id
    assert result.provider == "TESSERACT_OCR_V1"
    assert result.status == "SUCCESS"
    assert result.confidence_score >= 0.85
    assert result.confidence_category == ConfidenceCategory.HIGH

    # Verify structured fields
    fields = result.extracted_fields
    assert "Madhya Pradesh" in fields.get("state", "")
    assert "Bhopal" in fields.get("district", "")
    assert "Huzur" in fields.get("tehsil", "")
    assert "Bairagarh" in fields.get("village", "")
    assert "104/2" in fields.get("khasra_number", "")
    assert "45" in fields.get("khata_number", "")
    assert "Ram Prasad Sharma" in fields.get("owner_name", "")
    assert "PATTA-2024-889" in fields.get("patta_number", "")

    # Verify dual preservation (raw and normalized)
    struct = result.structured_fields
    assert struct["khasra_number"].value == "104/2"
    assert struct["khasra_number"].normalized_value == "104/2"
    assert struct["owner_name"].normalized_value == "Ram Prasad Sharma"
    assert struct["area_in_hectares"].normalized_value == 1.25

@pytest.mark.asyncio
async def test_tesseract_noisy_image_extraction_low_confidence():
    provider = TesseractOCRProvider()
    image_bytes = get_fixture_bytes("noisy_land_record.png")
    assert len(image_bytes) > 0, "noisy_land_record.png fixture must exist"

    doc_id = uuid.uuid4()
    result = await provider.extract_document_fields(
        document_id=doc_id,
        file_bytes=image_bytes,
        file_name="noisy_land_record.png",
        mime_type="image/png"
    )

    assert result.confidence_score < 0.60
    assert result.confidence_category == ConfidenceCategory.LOW
    assert len(result.low_confidence_fields) > 0

@pytest.mark.asyncio
async def test_tesseract_empty_document_rejection():
    provider = TesseractOCRProvider()
    with pytest.raises(ExtractionProcessingError) as exc:
        await provider.extract_document_fields(
            document_id=uuid.uuid4(),
            file_bytes=b"",
            file_name="empty.png",
            mime_type="image/png"
        )
    assert "empty" in str(exc.value).lower()

@pytest.mark.asyncio
async def test_tesseract_corrupt_image_rejection():
    provider = TesseractOCRProvider()
    corrupt_bytes = get_fixture_bytes("corrupt_record.png")
    with pytest.raises(ExtractionProcessingError) as exc:
        await provider.extract_document_fields(
            document_id=uuid.uuid4(),
            file_bytes=corrupt_bytes,
            file_name="corrupt_record.png",
            mime_type="image/png"
        )
    assert "corrupt" in str(exc.value).lower() or "unreadable" in str(exc.value).lower()

@pytest.mark.asyncio
async def test_tesseract_digital_pdf_extraction():
    provider = TesseractOCRProvider()
    pdf_bytes = get_fixture_bytes("clean_digital_record.pdf")
    assert len(pdf_bytes) > 0, "clean_digital_record.pdf fixture must exist"

    doc_id = uuid.uuid4()
    result = await provider.extract_document_fields(
        document_id=doc_id,
        file_bytes=pdf_bytes,
        file_name="clean_digital_record.pdf",
        mime_type="application/pdf"
    )

    assert result.status == "SUCCESS"
    assert result.confidence_category == ConfidenceCategory.HIGH
    assert "Madhya Pradesh" in result.extracted_fields.get("state", "")
    assert "104/2" in result.extracted_fields.get("khasra_number", "")
