import uuid
from app.core.config import settings
from fastapi import APIRouter, Depends, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.user import UserModel
from app.schemas.user import UserRole
from app.services.digitization_service import digitization_service
from app.services.document_service import document_service
from app.services.job_service import job_service
from app.schemas.pipeline import DigitizationPipelineResult
from app.schemas.job import JobResponse
from app.api.dependencies.auth import require_role

router = APIRouter(prefix="/digitization", tags=["Digitization Pipeline"])

@router.post("/queue-processing/{document_id}", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def queue_document_processing(
    document_id: uuid.UUID,
    current_user: UserModel = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Queues document for asynchronous background processing without blocking.
    Requires ADMIN or OPERATOR role and resource ownership.
    """
    doc = await document_service.get_document(session, document_id)
    document_service.check_document_access(doc, current_user)

    job = await job_service.create_job(session, document_id, created_by=current_user.id)
    await session.commit()
    job_service.dispatch_job(job.id)
    return JobResponse.model_validate(job)


@router.post("/process/{document_id}", response_model=DigitizationPipelineResult)
async def process_document_pipeline(
    document_id: uuid.UUID,
    current_user: UserModel = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Executes the full digitization workflow on an existing registered document:
    Requires ADMIN or OPERATOR role and resource ownership.
    """
    doc = await document_service.get_document(session, document_id)
    document_service.check_document_access(doc, current_user)

    result = await digitization_service.execute_pipeline(session, document_id)
    await session.commit()
    return result

@router.post("/upload-and-process", response_model=DigitizationPipelineResult, status_code=status.HTTP_201_CREATED)
async def upload_and_process_document(
    file: UploadFile = File(...),
    doc_type: str = Form("JAMABANDI"),
    current_user: UserModel = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Convenience endpoint: uploads physical document binary and executes pipeline.
    Requires ADMIN or OPERATOR role. Assigns ownership to current user.
    """
    content = await file.read(settings.MAX_UPLOAD_SIZE_BYTES + 1)
    mime_type = file.content_type or "application/octet-stream"
    
    # Register document with creator identity
    doc = await document_service.register_document(
        session=session,
        file_name=file.filename or "uploaded_document",
        mime_type=mime_type,
        file_bytes=content,
        doc_type=doc_type,
        created_by=current_user.id
    )
    result = await digitization_service.execute_pipeline(session, doc.id)
    await session.commit()
    return result
