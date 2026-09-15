import uuid
import pytest
from app.services.extraction.provider import MockExtractionProvider
from app.services.extraction.tesseract_provider import TesseractOCRProvider
from app.services.extraction.factory import get_extraction_provider
from app.schemas.extraction import ConfidenceCategory, categorize_confidence
from app.core.exceptions import ExtractionProcessingError, OCREngineUnavailableError

@pytest.mark.asyncio
async def test_mock_provider_structured_output():
    provider = MockExtractionProvider()
    doc_id = uuid.uuid4()
    content = b"%PDF-1.4 Simulated Revenue Record"

    result = await provider.extract_document_fields(
        document_id=doc_id,
        file_bytes=content,
        file_name="jamabandi_sample.pdf",
        mime_type="application/pdf"
    )

    assert result.document_id == doc_id
    assert result.provider == "MOCK_OCR_V1"
    assert result.status == "SUCCESS"
    assert 0.0 <= result.confidence_score <= 1.0
    assert result.confidence_category in {ConfidenceCategory.HIGH, ConfidenceCategory.MEDIUM, ConfidenceCategory.LOW}
    assert result.structured_fields is not None
    assert "owner_name" in result.structured_fields
    assert "khasra_number" in result.structured_fields
    assert "area_in_hectares" in result.structured_fields
    assert result.structured_fields["owner_name"].confidence >= 0.0

def test_ocr_provider_selection_factory():
    mock_prov = get_extraction_provider("MOCK")
    assert isinstance(mock_prov, MockExtractionProvider)
    assert mock_prov.provider_name == "MOCK_OCR_V1"

    tess_prov = get_extraction_provider("TESSERACT")
    assert isinstance(tess_prov, TesseractOCRProvider)
    assert tess_prov.provider_name == "TESSERACT_OCR_V1"

    with pytest.raises(OCREngineUnavailableError):
        get_extraction_provider("UNKNOWN_ENGINE_XYZ")

@pytest.mark.asyncio
async def test_tesseract_provider_unavailable_handling():
    # Points to non-existent binary path to test graceful failure
    provider = TesseractOCRProvider(tesseract_cmd="C:\\nonexistent\\path\\tesseract.exe")
    assert provider.is_available is False

    with pytest.raises(OCREngineUnavailableError) as exc_info:
        await provider.extract_document_fields(
            document_id=uuid.uuid4(),
            file_bytes=b"dummy image data",
            file_name="scan.png",
            mime_type="image/png"
        )
    assert "unavailable" in exc_info.value.message.lower()
    assert exc_info.value.status_code == 503

def test_confidence_bounds_and_categories():
    assert categorize_confidence(0.95) == ConfidenceCategory.HIGH
    assert categorize_confidence(0.85) == ConfidenceCategory.HIGH
    assert categorize_confidence(0.84) == ConfidenceCategory.MEDIUM
    assert categorize_confidence(0.60) == ConfidenceCategory.MEDIUM
    assert categorize_confidence(0.59) == ConfidenceCategory.LOW
    assert categorize_confidence(0.0) == ConfidenceCategory.LOW
    # Bounds clamping
    assert categorize_confidence(1.5) == ConfidenceCategory.HIGH
    assert categorize_confidence(-0.5) == ConfidenceCategory.LOW

@pytest.mark.asyncio
async def test_empty_and_corrupt_rejection():
    provider = MockExtractionProvider()
    with pytest.raises(ExtractionProcessingError):
        await provider.extract_document_fields(
            document_id=uuid.uuid4(),
            file_bytes=b"",
            file_name="empty.pdf",
            mime_type="application/pdf"
        )

    with pytest.raises(ExtractionProcessingError):
        await provider.extract_document_fields(
            document_id=uuid.uuid4(),
            file_bytes=b"corrupt data",
            file_name="corrupt_scan.pdf",
            mime_type="application/pdf"
        )
