import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.document_service import DocumentService
from app.core.exceptions import DocumentNotFoundError, InvalidStateTransitionError

@pytest.mark.anyio
async def test_document_lifecycle(db_session: AsyncSession):
    service = DocumentService()
    
    # 1. Registration
    doc = await service.register_document(
        session=db_session,
        file_name="khasra_bhopal.pdf",
        mime_type="application/pdf",
        file_bytes=b"sample binary content",
        doc_type="KHASRA_RECORD",
        metadata={"district": "Bhopal"}
    )
    assert doc.id is not None
    assert doc.status == "UPLOADED"
    assert doc.file_size_bytes == len(b"sample binary content")

    # 2. Retrieval
    fetched = await service.get_document(db_session, doc.id)
    assert fetched.file_name == "khasra_bhopal.pdf"

    # 3. Valid State Transition: UPLOADED -> PROCESSING
    updated = await service.update_status(db_session, doc.id, "PROCESSING")
    assert updated.status == "PROCESSING"

    # 4. Valid State Transition: PROCESSING -> EXTRACTED
    updated = await service.update_status(db_session, doc.id, "EXTRACTED")
    assert updated.status == "EXTRACTED"
    assert updated.processed_at is not None

    # 5. Invalid State Transition: EXTRACTED cannot jump directly to UPLOADED
    with pytest.raises(InvalidStateTransitionError):
        await service.update_status(db_session, doc.id, "UPLOADED")

    # 6. Not Found Error
    with pytest.raises(DocumentNotFoundError):
        await service.get_document(db_session, uuid.uuid4())
