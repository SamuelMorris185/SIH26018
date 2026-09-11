import uuid
import pytest
from app.services.extraction.provider import MockExtractionProvider

@pytest.mark.anyio
async def test_mock_extraction_provider():
    provider = MockExtractionProvider()
    assert provider.provider_name == "MOCK_OCR_V1"

    doc_id = uuid.uuid4()
    dummy_bytes = b"%PDF-1.4 sample document content"

    payload = await provider.extract_document_fields(
        document_id=doc_id,
        file_bytes=dummy_bytes,
        file_name="sample_khasra.pdf",
        mime_type="application/pdf"
    )

    assert payload.document_id == doc_id
    assert payload.provider == "MOCK_OCR_V1"
    assert payload.status == "SUCCESS"
    assert "state" in payload.extracted_fields
    assert "khasra_number" in payload.extracted_fields
    assert payload.confidence_score >= 0.80
    assert payload.raw_text is not None
    assert "SIMULATION" in payload.raw_text
