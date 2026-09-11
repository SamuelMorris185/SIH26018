import os
import uuid
import pytest
from pathlib import Path
from app.services.storage_service import LocalStorageService
from app.services.document_service import DocumentService
from app.services.extraction.provider import MockExtractionProvider
from app.core.exceptions import (
    OversizedFileError,
    UnsupportedFileTypeError,
    MissingFileError,
    ExtractionProcessingError,
)

def test_path_traversal_prevention(tmp_path: Path):
    storage = LocalStorageService(base_dir=str(tmp_path))

    # Dangerous filenames attempting directory escape
    dangerous_names = [
        "../../etc/passwd",
        "..\\..\\windows\\system32\\cmd.exe",
        "nested/../../secret.pdf"
    ]

    for name in dangerous_names:
        sanitized = storage._sanitize_filename(name)
        assert "/" not in sanitized
        assert "\\" not in sanitized
        assert ".." not in sanitized

def test_file_exists_and_missing_file_detection(tmp_path: Path):
    storage = LocalStorageService(base_dir=str(tmp_path))

    assert storage.file_exists(str(tmp_path / "non_existent.pdf")) is False

    # Create dummy file
    dummy_file = tmp_path / "valid.pdf"
    dummy_file.write_bytes(b"%PDF dummy")
    assert storage.file_exists(str(dummy_file)) is True

@pytest.mark.anyio
async def test_oversized_file_rejection(tmp_path: Path):
    doc_service = DocumentService(storage=LocalStorageService(base_dir=str(tmp_path)))

    # 15 MB payload exceeding the 10 MB default limit
    oversized_bytes = b"0" * (11 * 1024 * 1024)

    with pytest.raises(OversizedFileError) as exc_info:
        doc_service.validate_file_upload(
            file_name="huge_scan.pdf",
            mime_type="application/pdf",
            file_bytes=oversized_bytes
        )
    assert "exceeds maximum permitted upload limit" in exc_info.value.message
    assert exc_info.value.status_code == 413

def test_unsupported_file_type_rejection(tmp_path: Path):
    doc_service = DocumentService(storage=LocalStorageService(base_dir=str(tmp_path)))

    # 1. Disallowed extension
    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        doc_service.validate_file_upload(
            file_name="malicious.exe",
            mime_type="application/pdf",
            file_bytes=b"sample"
        )
    assert exc_info.value.status_code == 415

    # 2. Disallowed MIME type
    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        doc_service.validate_file_upload(
            file_name="document.txt",
            mime_type="text/plain",
            file_bytes=b"sample"
        )
    assert exc_info.value.status_code == 415

@pytest.mark.anyio
async def test_mock_extraction_empty_and_corrupt_files():
    provider = MockExtractionProvider()
    doc_id = uuid.uuid4()

    # Empty file rejection
    with pytest.raises(ExtractionProcessingError) as exc_info:
        await provider.extract_document_fields(
            document_id=doc_id,
            file_bytes=b"",
            file_name="empty.pdf",
            mime_type="application/pdf"
        )
    assert "empty" in exc_info.value.message

    # Corrupted scan rejection trigger
    with pytest.raises(ExtractionProcessingError) as exc_info:
        await provider.extract_document_fields(
            document_id=doc_id,
            file_bytes=b"corrupted bytes",
            file_name="corrupt_page_01.pdf",
            mime_type="application/pdf"
        )
    assert "could not decipher" in exc_info.value.message

@pytest.mark.anyio
async def test_mock_extraction_confidence_bounds():
    provider = MockExtractionProvider()
    doc_id = uuid.uuid4()

    payload = await provider.extract_document_fields(
        document_id=doc_id,
        file_bytes=b"%PDF valid content",
        file_name="jamabandi.pdf",
        mime_type="application/pdf"
    )

    assert 0.0 <= payload.confidence_score <= 1.0
    for field, conf in (payload.field_confidences or {}).items():
        assert 0.0 <= conf <= 1.0
