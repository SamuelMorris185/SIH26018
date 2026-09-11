import uuid
import re
import asyncio
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.core.logging import logger
from app.core.exceptions import (
    JobNotFoundError,
    DuplicateProcessingError,
    JobNotRetryableError,
    ForbiddenError,
)
from app.models.job import JobModel
from app.models.user import UserModel
from app.schemas.user import UserRole
from app.schemas.job import JobResponse
from app.services.audit_service import audit_service
from app.services.digitization_service import digitization_service

def sanitize_error_message(raw_msg: str) -> str:
    """
    Strips internal filesystem paths, tracebacks, and sensitive host markers from error messages.
    """
    if not raw_msg:
        return "Processing error occurred."
    msg = str(raw_msg)
    # Strip Windows file paths (e.g. C:\path\to\file or C:/path/to/file)
    msg = re.sub(r"[a-zA-Z]:[\\/][^\s\"']+", "[PATH_REDACTED]", msg)
    # Strip Unix file paths (e.g. /home/user/... or /tmp/...)
    msg = re.sub(r"(?:/[a-zA-Z0-9._-]+)+", "[PATH_REDACTED]", msg)
    # Strip Python traceback blocks
    msg = re.sub(r"Traceback \(most recent call last\):.*", "[TRACEBACK_REDACTED]", msg, flags=re.DOTALL)
    # Strip file frame markers
    msg = re.sub(r'File "[^"]+", line \d+, in \w+', "[FRAME_REDACTED]", msg)
    if len(msg) > 480:
        msg = msg[:477] + "..."
    return msg.strip()

def classify_error(exc: Exception) -> str:
    """
    Classifies an exception into standard categories without leaking internal classes.
    """
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    if any(k in name or k in msg for k in ["file", "storage", "path", "missingfile", "filenotfound"]):
        return "STORAGE_ERROR"
    if any(k in name or k in msg for k in ["ocr", "extract", "tesseract", "parsing"]):
        return "EXTRACTION_ERROR"
    if any(k in name or k in msg for k in ["valid", "rule", "mismatch", "format"]):
        return "VALIDATION_ERROR"
    return "UNEXPECTED_ERROR"

class JobService:
    """
    Persistent Job Management and Asynchronous Execution Service.
    Enforces idempotency, duplicate prevention, sanitized errors, and RBAC isolation.
    """

    def __init__(self, session_maker: Optional[Callable[[], AsyncSession]] = None):
        self._session_maker = session_maker
        self._active_tasks: Dict[uuid.UUID, asyncio.Task] = {}

    @property
    def session_maker(self):
        if self._session_maker:
            return self._session_maker
        from app.db.session import AsyncSessionLocal
        return AsyncSessionLocal

    @session_maker.setter
    def session_maker(self, maker: Callable[[], AsyncSession]):
        self._session_maker = maker

    def check_job_access(self, job: JobModel, current_user: UserModel) -> None:
        """
        Enforces RBAC: Only ADMIN or document/job owners may inspect or retry a job.
        """
        if current_user.role == UserRole.ADMIN or str(current_user.role) == "ADMIN":
            return
        if job.created_by and job.created_by == current_user.id:
            return
        if job.document and job.document.created_by == current_user.id:
            return
        raise ForbiddenError("You do not have permission to access or manage this processing job.")

    async def get_job(self, session: AsyncSession, job_id: uuid.UUID) -> JobModel:
        """
        Retrieves a job by its unique UUID.
        """
        result = await session.execute(select(JobModel).where(JobModel.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise JobNotFoundError(job_id)
        return job

    async def check_active_job(self, session: AsyncSession, document_id: uuid.UUID) -> Optional[JobModel]:
        """
        Checks if there is already an active job (QUEUED or PROCESSING) for the document.
        """
        query = select(JobModel).where(
            JobModel.document_id == document_id,
            JobModel.status.in_(["QUEUED", "PROCESSING"])
        ).order_by(desc(JobModel.created_at)).limit(1)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def create_job(
        self,
        session: AsyncSession,
        document_id: uuid.UUID,
        created_by: Optional[uuid.UUID] = None
    ) -> JobModel:
        """
        Creates a new persistent processing job in QUEUED status.
        Guarantees concurrency prevention by rejecting duplicate active jobs.
        """
        active_job = await self.check_active_job(session, document_id)
        if active_job:
            logger.warning(f"Rejected duplicate job for document {document_id}: already active job {active_job.id}")
            raise DuplicateProcessingError(document_id, active_job.id)

        job = JobModel(
            id=uuid.uuid4(),
            document_id=document_id,
            created_by=created_by,
            status="QUEUED",
            current_stage="QUEUED",
            progress_percentage=0,
            retry_count=0,
            max_retries=3,
            created_at=datetime.utcnow()
        )
        session.add(job)
        await session.flush()

        # Append-only audit logging for job queueing
        await audit_service.log_event(
            session=session,
            action="JOB_QUEUED",
            entity_type="JOB",
            actor_user_id=created_by,
            entity_id=job.id,
            new_state={"document_id": str(document_id), "status": "QUEUED"}
        )
        logger.info(f"Created processing job {job.id} for document {document_id}")
        return job

    async def list_jobs(
        self,
        session: AsyncSession,
        current_user: UserModel,
        document_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Tuple[int, List[JobModel]]:
        """
        Retrieves paginated list of jobs with resource isolation for non-admin users.
        """
        query = select(JobModel)
        count_query = select(func.count(JobModel.id))

        filters = []
        is_admin = current_user.role == UserRole.ADMIN or str(current_user.role) == "ADMIN"
        if not is_admin:
            filters.append(JobModel.created_by == current_user.id)
        if document_id:
            filters.append(JobModel.document_id == document_id)
        if status_filter:
            filters.append(JobModel.status == status_filter.upper())

        if filters:
            query = query.where(*filters)
            count_query = count_query.where(*filters)

        total_res = await session.execute(count_query)
        total = total_res.scalar_one()

        offset = (page - 1) * limit
        res = await session.execute(
            query.order_by(desc(JobModel.created_at)).offset(offset).limit(limit)
        )
        jobs = list(res.scalars().all())
        return total, jobs

    async def retry_job(
        self,
        session: AsyncSession,
        job_id: uuid.UUID,
        current_user: UserModel
    ) -> JobModel:
        """
        Retries a failed job if under max_retries limit and no other active job is running for document.
        """
        job = await self.get_job(session, job_id)
        self.check_job_access(job, current_user)

        if job.status != "FAILED":
            raise JobNotRetryableError(
                f"Job {job_id} is in status '{job.status}' and cannot be retried. Only FAILED jobs are eligible for retry."
            )

        if job.retry_count >= job.max_retries:
            raise JobNotRetryableError(
                f"Job {job_id} has reached the maximum retry limit ({job.max_retries})."
            )

        # Ensure no other active job is processing this document
        active = await self.check_active_job(session, job.document_id)
        if active and active.id != job.id:
            raise DuplicateProcessingError(job.document_id, active.id)

        # Transition to RETRYING then QUEUED
        job.retry_count += 1
        job.status = "RETRYING"
        job.current_stage = "QUEUED"
        job.progress_percentage = 0
        job.error_category = None
        job.error_message = None
        job.started_at = None
        job.completed_at = None
        job.result_summary = None
        await session.flush()

        job.status = "QUEUED"
        await session.flush()

        await audit_service.log_event(
            session=session,
            action="JOB_RETRIED",
            entity_type="JOB",
            actor_user_id=current_user.id,
            entity_id=job.id,
            new_state={"retry_count": job.retry_count, "status": "QUEUED"}
        )
        logger.info(f"Retrying job {job.id} (attempt {job.retry_count}/{job.max_retries})")

        # Dispatch background worker task
        self.dispatch_job(job.id)
        return job

    def dispatch_job(self, job_id: uuid.UUID) -> asyncio.Task:
        """
        Spawns background task for asynchronous job execution.
        """
        task = asyncio.create_task(self.run_job_worker(job_id))
        self._active_tasks[job_id] = task

        def _cleanup(fut):
            self._active_tasks.pop(job_id, None)

        task.add_done_callback(_cleanup)
        return task

    async def run_job_worker(self, job_id: uuid.UUID) -> None:
        """
        Core background worker loop executing the digitization pipeline.
        Manages persistent stages, progress, error sanitization, and audit trails.
        """
        maker = self.session_maker
        async with maker() as session:
            job = await self.get_job(session, job_id)
            doc_id = job.document_id
            user_id = job.created_by

            # Transition to PROCESSING
            job.status = "PROCESSING"
            job.current_stage = "STORAGE_READ"
            job.progress_percentage = 15
            job.started_at = datetime.utcnow()
            await session.commit()

            await audit_service.log_event(
                session=session,
                action="JOB_STARTED",
                entity_type="JOB",
                actor_user_id=user_id,
                entity_id=job.id,
                new_state={"status": "PROCESSING", "stage": "STORAGE_READ"}
            )
            await session.commit()

            try:
                # Update stage progress through execution
                job.current_stage = "OCR_EXTRACTION"
                job.progress_percentage = 35
                await session.commit()

                # Execute core pipeline
                pipeline_result = await digitization_service.execute_pipeline(session, doc_id)

                # Job Completed successfully
                job.status = "COMPLETED"
                job.current_stage = "COMPLETED"
                job.progress_percentage = 100
                job.completed_at = datetime.utcnow()
                job.result_summary = {
                    "document_id": str(doc_id),
                    "document_status": pipeline_result.document.status,
                    "records_count": len(pipeline_result.records),
                    "total_discrepancies": (
                        pipeline_result.discrepancies.total_discrepancies
                        if pipeline_result.discrepancies else 0
                    ),
                    "summary": pipeline_result.summary
                }
                await session.commit()

                await audit_service.log_event(
                    session=session,
                    action="JOB_COMPLETED",
                    entity_type="JOB",
                    actor_user_id=user_id,
                    entity_id=job.id,
                    new_state={
                        "status": "COMPLETED",
                        "records_count": len(pipeline_result.records)
                    }
                )
                await session.commit()
                logger.info(f"Background job {job.id} completed successfully for document {doc_id}")

            except Exception as exc:
                cat = classify_error(exc)
                sanitized_msg = sanitize_error_message(str(exc))
                logger.error(f"Background job {job.id} failed [{cat}]: {sanitized_msg}")

                job.status = "FAILED"
                job.current_stage = "FAILED"
                job.error_category = cat
                job.error_message = sanitized_msg
                job.completed_at = datetime.utcnow()
                await session.commit()

                await audit_service.log_event(
                    session=session,
                    action="JOB_FAILED",
                    entity_type="JOB",
                    actor_user_id=user_id,
                    entity_id=job.id,
                    new_state={"status": "FAILED", "error_category": cat, "error_message": sanitized_msg}
                )
                await session.commit()

job_service = JobService()
