import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.user import UserModel
from app.schemas.user import UserRole
from app.schemas.job import JobResponse, JobPaginatedList
from app.services.job_service import job_service
from app.api.dependencies.auth import get_current_user, require_role

router = APIRouter(prefix="/jobs", tags=["Processing Jobs"])

@router.get("", response_model=JobPaginatedList)
async def list_jobs(
    document_id: Optional[uuid.UUID] = Query(None, description="Filter jobs by document ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter jobs by status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Lists paginated processing jobs with ownership isolation for non-admin users.
    """
    total, jobs = await job_service.list_jobs(
        session=session,
        current_user=current_user,
        document_id=document_id,
        status_filter=status_filter,
        page=page,
        limit=limit
    )
    return JobPaginatedList(
        total=total,
        page=page,
        limit=limit,
        data=[JobResponse.model_validate(j) for j in jobs]
    )

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: uuid.UUID,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Retrieves the status, stage progress, and error details of an asynchronous processing job.
    Enforces RBAC and resource ownership isolation.
    """
    job = await job_service.get_job(session, job_id)
    job_service.check_job_access(job, current_user)
    return JobResponse.model_validate(job)

@router.post("/{job_id}/retry", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def retry_job(
    job_id: uuid.UUID,
    current_user: UserModel = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Retries execution of a FAILED processing job.
    Requires ADMIN or OPERATOR role and resource ownership.
    """
    job = await job_service.retry_job(session, job_id, current_user)
    await session.commit()
    job_service.dispatch_job(job.id)
    return JobResponse.model_validate(job)
