import uuid
from typing import Optional, List, Union
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.session import get_db_session
from app.models.user import UserModel
from app.models.job import JobModel
from app.schemas.user import UserRole
from app.services.document_service import document_service
from app.services.digitization_service import digitization_service
from app.services.land_record_service import land_record_service
from app.services.job_service import job_service
from app.schemas.document import DocumentResponse, DocumentPaginatedList
from app.schemas.record import LandRecordResponse
from app.schemas.pipeline import DigitizationPipelineResult
from app.schemas.job import JobResponse
from app.core.exceptions import DuplicateProcessingError
from app.api.dependencies.auth import get_current_user, require_role


router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form("JAMABANDI"),
    current_user: UserModel = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Registers a new physical land document in storage and database.
    Requires ADMIN or OPERATOR role. Assigns ownership to authenticated user.
    """
    content = await file.read()
    mime_type = file.content_type or "application/octet-stream"
    doc = await document_service.register_document(
        session=session,
        file_name=file.filename or "uploaded_document",
        mime_type=mime_type,
        file_bytes=content,
        doc_type=doc_type,
        created_by=current_user.id
    )
    await session.commit()
    return document_service.to_response_dto(doc)

@router.get("", response_model=DocumentPaginatedList)
async def list_documents(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    doc_type: Optional[str] = Query(None, description="Filter by document type"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Retrieves paginated list of registered documents for authenticated users.
    """
    total, docs = await document_service.list_documents(
        session=session,
        status_filter=status_filter,
        doc_type_filter=doc_type,
        page=page,
        limit=limit
    )
    return DocumentPaginatedList(
        total=total,
        page=page,
        limit=limit,
        data=[document_service.to_response_dto(d) for d in docs]
    )

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Retrieves safe metadata for a specific document with resource authorization.
    """
    doc = await document_service.get_document(session, document_id)
    document_service.check_document_access(doc, current_user)
    return document_service.to_response_dto(doc)

@router.get("/{document_id}/content")
async def get_document_content(
    document_id: uuid.UUID,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Securely streams raw document binary content (PDF/image) for viewing or preview.
    Enforces RBAC and document resource ownership checks.
    """
    doc = await document_service.get_document(session, document_id)
    document_service.check_document_access(doc, current_user)
    
    file_bytes = await document_service.storage.read_file(doc.file_path)
    return Response(
        content=file_bytes,
        media_type=doc.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'inline; filename="{doc.file_name}"',
            "Cache-Control": "private, max-age=3600",
        }
    )

@router.post(
    "/{document_id}/process",
    response_model=Union[JobResponse, DigitizationPipelineResult],
    responses={
        200: {"model": DigitizationPipelineResult, "description": "Synchronous processing completed successfully"},
        202: {"model": JobResponse, "description": "Processing job queued for background execution"},
    }
)
async def process_document(
    document_id: uuid.UUID,
    background: bool = Query(False, description="Execute processing asynchronously in background"),
    response: Response = None,
    current_user: UserModel = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Initiates the complete land-record processing workflow on a registered document.
    When background=True, creates a persistent job, triggers async execution, and returns HTTP 202.
    When background=False, processes synchronously and returns DigitizationPipelineResult (HTTP 200).
    Requires ADMIN or OPERATOR role and resource ownership.
    """
    doc = await document_service.get_document(session, document_id)
    document_service.check_document_access(doc, current_user)

    if background:
        job = await job_service.create_job(session, document_id, created_by=current_user.id)
        await session.commit()
        job_service.dispatch_job(job.id)
        if response:
            response.status_code = status.HTTP_202_ACCEPTED
        return JobResponse.model_validate(job)

    # Synchronous mode: verify no active background job is running
    active = await job_service.check_active_job(session, document_id)
    if active:
        raise DuplicateProcessingError(document_id, active.id)

    result = await digitization_service.execute_pipeline(session, document_id)
    await session.commit()
    return result

@router.get("/{document_id}/jobs", response_model=List[JobResponse])
async def get_document_jobs(
    document_id: uuid.UUID,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Retrieves all asynchronous processing jobs (active and historical) for a specific document.
    """
    doc = await document_service.get_document(session, document_id)
    document_service.check_document_access(doc, current_user)

    query = select(JobModel).where(JobModel.document_id == document_id).order_by(desc(JobModel.created_at))
    res = await session.execute(query)
    jobs = list(res.scalars().all())
    return [JobResponse.model_validate(j) for j in jobs]

@router.get("/{document_id}/records", response_model=List[LandRecordResponse])
async def get_document_records(
    document_id: uuid.UUID,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Retrieves all land records extracted from a specific document.
    """
    doc = await document_service.get_document(session, document_id)
    document_service.check_document_access(doc, current_user)
    records = await land_record_service.list_by_document(session, document_id)
    return [LandRecordResponse.model_validate(r) for r in records]

