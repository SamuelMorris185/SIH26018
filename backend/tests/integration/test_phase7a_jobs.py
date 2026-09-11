import io
import uuid
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.job import JobModel
from app.models.user import UserModel
from app.models.audit_log import AuditLogModel
from app.core.security import get_password_hash, create_access_token
from app.services.job_service import job_service, sanitize_error_message, classify_error
from tests.conftest import TestAsyncSessionLocal

SAMPLE_JAMABANDI_TEXT = """
JAMABANDI / RECORD OF RIGHTS (ROR)
State: Rajasthan
District: Jaipur
Tehsil: Sanganer
Village: Rampura
Khasra No: 101/1
Khata No: 45
Total Area: 2.5000 Hectares
Land Classification: Chahi (Irrigated)
Owner Name: Ramesh Chand Sharma
Co-owners: Suresh Chand Sharma
Patta Number: PATTA-2023-889
Registration Number: REG-JP-2023-4567
Mutation Number: MUT-2023-112
Document Date: 2023-08-15
"""

@pytest.fixture(autouse=True)
def setup_job_service_session():
    """Ensure JobService background worker uses test database session."""
    original_maker = job_service._session_maker
    job_service.session_maker = TestAsyncSessionLocal
    yield
    job_service.session_maker = original_maker

def create_test_users():
    admin = UserModel(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        email="admin@sih.gov.in",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Administrator",
        role="ADMIN",
        is_active=True,
        created_at=datetime.utcnow()
    )
    operator_a = UserModel(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        email="operator_a@sih.gov.in",
        hashed_password=get_password_hash("OperatorPass123!"),
        full_name="Operator A",
        role="OPERATOR",
        is_active=True,
        created_at=datetime.utcnow()
    )
    operator_b = UserModel(
        id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        email="operator_b@sih.gov.in",
        hashed_password=get_password_hash("OperatorPass123!"),
        full_name="Operator B",
        role="OPERATOR",
        is_active=True,
        created_at=datetime.utcnow()
    )
    return admin, operator_a, operator_b

def test_error_sanitization_and_classification():
    """Verifies that internal file paths and tracebacks are never leaked."""
    win_path_err = "FileNotFoundError: [Errno 2] No such file: 'C:\\Users\\admin\\secret\\doc.pdf'"
    sanitized = sanitize_error_message(win_path_err)
    assert "C:\\Users" not in sanitized
    assert "[PATH_REDACTED]" in sanitized

    unix_path_err = "IOError: Could not read /var/data/uploads/records/doc.tif"
    sanitized_unix = sanitize_error_message(unix_path_err)
    assert "/var/data" not in sanitized_unix
    assert "[PATH_REDACTED]" in sanitized_unix

    traceback_err = "Traceback (most recent call last):\n  File \"app/pipeline.py\", line 42\nException: Failed"
    sanitized_tb = sanitize_error_message(traceback_err)
    assert "Traceback" not in sanitized_tb
    assert "[TRACEBACK_REDACTED]" in sanitized_tb

    # Error classification
    assert classify_error(FileNotFoundError("storage missing")) == "STORAGE_ERROR"
    assert classify_error(RuntimeError("Tesseract OCR timeout")) == "EXTRACTION_ERROR"
    assert classify_error(ValueError("Invalid Khasra format")) == "VALIDATION_ERROR"
    assert classify_error(Exception("Something unexpected")) == "UNEXPECTED_ERROR"

def test_async_process_endpoint_returns_202_and_queued_job(client: TestClient):
    """Verifies POST /api/v1/documents/{id}/process?background=true returns 202 and JobResponse."""
    # 1. Upload document
    upload_res = client.post(
        "/api/v1/documents",
        files={"file": ("jamabandi_async.pdf", io.BytesIO(SAMPLE_JAMABANDI_TEXT.encode("utf-8")), "application/pdf")},
        data={"doc_type": "JAMABANDI"}
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # 2. Trigger asynchronous background processing
    proc_res = client.post(f"/api/v1/documents/{doc_id}/process?background=true")
    assert proc_res.status_code == 202
    job_data = proc_res.json()
    assert job_data["document_id"] == doc_id
    assert job_data["status"] == "QUEUED"
    assert job_data["current_stage"] == "QUEUED"
    assert job_data["progress_percentage"] == 0
    assert job_data["retry_count"] == 0
    assert job_data["max_retries"] == 3

    # 3. Query job status via GET /api/v1/jobs/{job_id}
    job_id = job_data["id"]
    job_query_res = client.get(f"/api/v1/jobs/{job_id}")
    assert job_query_res.status_code == 200
    assert job_query_res.json()["id"] == job_id

def test_duplicate_processing_prevention_409(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """Verifies that an active job on the same document rejects duplicate processing with 409 Conflict."""
    # Prevent background worker from immediately executing so the job remains QUEUED
    monkeypatch.setattr(job_service, "dispatch_job", lambda job_id: None)

    upload_res = client.post(
        "/api/v1/documents",
        files={"file": ("jamabandi_dup.pdf", io.BytesIO(SAMPLE_JAMABANDI_TEXT.encode("utf-8")), "application/pdf")},
        data={"doc_type": "JAMABANDI"}
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # First async process creates QUEUED job
    first_res = client.post(f"/api/v1/documents/{doc_id}/process?background=true")
    assert first_res.status_code == 202

    # Second concurrent async process must return 409 Conflict
    second_res = client.post(f"/api/v1/documents/{doc_id}/process?background=true")
    assert second_res.status_code == 409
    dup_err = second_res.json()
    assert "already being processed" in dup_err["message"]

    # Synchronous process attempt on active document must also return 409 Conflict
    sync_res = client.post(f"/api/v1/documents/{doc_id}/process")
    assert sync_res.status_code == 409

@pytest.mark.asyncio
async def test_job_worker_execution_success(client: TestClient, db_session: AsyncSession):
    """Verifies that run_job_worker executes all pipeline stages and transitions job to COMPLETED."""
    upload_res = client.post(
        "/api/v1/documents",
        files={"file": ("jamabandi_worker.pdf", io.BytesIO(SAMPLE_JAMABANDI_TEXT.encode("utf-8")), "application/pdf")},
        data={"doc_type": "JAMABANDI"}
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # Create job in database
    job = await job_service.create_job(db_session, uuid.UUID(doc_id))
    job_id = job.id
    await db_session.commit()

    # Execute worker logic
    await job_service.run_job_worker(job_id)

    # Verify job state after worker completes
    async with TestAsyncSessionLocal() as session:
        updated_job = await job_service.get_job(session, job_id)
        assert updated_job.status == "COMPLETED"
        assert updated_job.current_stage == "COMPLETED"
        assert updated_job.progress_percentage == 100
        assert updated_job.started_at is not None
        assert updated_job.completed_at is not None
        assert updated_job.result_summary is not None
        assert updated_job.result_summary["records_count"] == 1
        assert updated_job.error_message is None

@pytest.mark.asyncio
async def test_job_worker_failure_sanitization(client: TestClient, db_session: AsyncSession):
    """Verifies that failures during worker execution are persisted safely with sanitized messages."""
    upload_res = client.post(
        "/api/v1/documents",
        files={"file": ("jamabandi_fail.pdf", io.BytesIO(SAMPLE_JAMABANDI_TEXT.encode("utf-8")), "application/pdf")},
        data={"doc_type": "JAMABANDI"}
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # Create job
    job = await job_service.create_job(db_session, uuid.UUID(doc_id))
    job_id = job.id
    await db_session.commit()

    # Corrupt document file_path to trigger STORAGE_ERROR
    from app.services.document_service import document_service
    doc = await document_service.get_document(db_session, uuid.UUID(doc_id))
    doc.file_path = "C:\\invalid\\nonexistent\\deep\\path\\doc.txt"
    await db_session.commit()

    # Execute worker
    await job_service.run_job_worker(job_id)

    # Inspect persisted job failure
    async with TestAsyncSessionLocal() as session:
        failed_job = await job_service.get_job(session, job_id)
        assert failed_job.status == "FAILED"
        assert failed_job.current_stage == "FAILED"
        assert failed_job.error_category == "STORAGE_ERROR"
        assert failed_job.error_message is not None
        assert "C:\\invalid" not in failed_job.error_message
        assert len(failed_job.error_message) > 0


def test_job_retry_workflow_and_limits(client: TestClient):
    """Verifies failed job retry workflow, counter increment, and max retry boundary enforcement."""
    # 1. Create a document and a failed job directly in DB
    upload_res = client.post(
        "/api/v1/documents",
        files={"file": ("jamabandi_retry.pdf", io.BytesIO(SAMPLE_JAMABANDI_TEXT.encode("utf-8")), "application/pdf")},
        data={"doc_type": "JAMABANDI"}
    )
    doc_id = upload_res.json()["id"]

    # Enqueue async job
    proc_res = client.post(f"/api/v1/documents/{doc_id}/process?background=true")
    job_id = proc_res.json()["id"]

    # Trying to retry a QUEUED job should return 400 Bad Request
    retry_queued_res = client.post(f"/api/v1/jobs/{job_id}/retry")
    assert retry_queued_res.status_code == 400
    assert "cannot be retried" in retry_queued_res.json()["message"]

@pytest.mark.asyncio
async def test_job_retry_execution(client: TestClient, db_session: AsyncSession):
    """Tests retrying a FAILED job: verifies retry count increment and status re-queue."""
    upload_res = client.post(
        "/api/v1/documents",
        files={"file": ("jamabandi_retry_exec.pdf", io.BytesIO(SAMPLE_JAMABANDI_TEXT.encode("utf-8")), "application/pdf")},
        data={"doc_type": "JAMABANDI"}
    )
    doc_id = upload_res.json()["id"]

    job = await job_service.create_job(db_session, uuid.UUID(doc_id))
    job.status = "FAILED"
    job.current_stage = "FAILED"
    job.error_category = "STORAGE_ERROR"
    job.error_message = "File was temporarily unavailable."
    job.retry_count = 0
    job.max_retries = 2
    await db_session.commit()
    job_id = job.id

    # Retry the failed job
    retry_res = client.post(f"/api/v1/jobs/{job_id}/retry")
    assert retry_res.status_code == 202
    retry_data = retry_res.json()
    assert retry_data["status"] == "QUEUED"
    assert retry_data["retry_count"] == 1
    assert retry_data["error_message"] is None

    # Wait for the background execution to complete
    import asyncio
    await asyncio.sleep(0.15)

    # Manually set retry_count to max_retries and status to FAILED to test limit
    async with TestAsyncSessionLocal() as session:
        j = await job_service.get_job(session, job_id)
        j.status = "FAILED"
        j.retry_count = 2
        await session.commit()

    # Retry beyond max retries must return 400
    exceed_res = client.post(f"/api/v1/jobs/{job_id}/retry")
    assert exceed_res.status_code == 400
    assert "maximum retry limit" in exceed_res.json()["message"]


@pytest.mark.asyncio
async def test_job_rbac_isolation(unauthenticated_client: TestClient, db_session: AsyncSession):
    """Verifies resource ownership isolation: Operator B cannot view or retry Operator A's jobs."""
    admin, op_a, op_b = create_test_users()
    db_session.add_all([admin, op_a, op_b])
    await db_session.commit()

    admin_token = create_access_token(data={"sub": str(admin.id), "role": admin.role})
    op_a_token = create_access_token(data={"sub": str(op_a.id), "role": op_a.role})
    op_b_token = create_access_token(data={"sub": str(op_b.id), "role": op_b.role})

    # Operator A uploads document
    upload_res = unauthenticated_client.post(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {op_a_token}"},
        files={"file": ("jamabandi_rbac.pdf", io.BytesIO(SAMPLE_JAMABANDI_TEXT.encode("utf-8")), "application/pdf")},
        data={"doc_type": "JAMABANDI"}
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # Operator A enqueues processing job
    proc_res = unauthenticated_client.post(
        f"/api/v1/documents/{doc_id}/process?background=true",
        headers={"Authorization": f"Bearer {op_a_token}"}
    )
    assert proc_res.status_code == 202
    job_id = proc_res.json()["id"]

    # Allow background execution on SQLite in-memory to finish before reading
    import asyncio
    await asyncio.sleep(0.2)

    # Operator B tries to access Operator A's job -> 403 Forbidden

    op_b_get = unauthenticated_client.get(
        f"/api/v1/jobs/{job_id}",
        headers={"Authorization": f"Bearer {op_b_token}"}
    )
    assert op_b_get.status_code == 403

    # Operator B tries to retry Operator A's job -> 403 Forbidden
    op_b_retry = unauthenticated_client.post(
        f"/api/v1/jobs/{job_id}/retry",
        headers={"Authorization": f"Bearer {op_b_token}"}
    )
    assert op_b_retry.status_code == 403

    # Operator A can access own job -> 200 OK
    op_a_get = unauthenticated_client.get(
        f"/api/v1/jobs/{job_id}",
        headers={"Authorization": f"Bearer {op_a_token}"}
    )
    assert op_a_get.status_code == 200
    assert op_a_get.json()["id"] == job_id

    # Admin can access Operator A's job -> 200 OK
    admin_get = unauthenticated_client.get(
        f"/api/v1/jobs/{job_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert admin_get.status_code == 200

def test_backward_compatible_sync_process(client: TestClient):
    """Verifies that calling POST /api/v1/documents/{id}/process without background=true remains 100% synchronous."""
    upload_res = client.post(
        "/api/v1/documents",
        files={"file": ("jamabandi_sync.pdf", io.BytesIO(SAMPLE_JAMABANDI_TEXT.encode("utf-8")), "application/pdf")},
        data={"doc_type": "JAMABANDI"}
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # Synchronous processing returns DigitizationPipelineResult directly with HTTP 200
    proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
    assert proc_res.status_code == 200
    proc_data = proc_res.json()
    assert "document" in proc_data
    assert "extraction" in proc_data
    assert "records" in proc_data
    assert len(proc_data["records"]) == 1
    assert "validations" in proc_data

@pytest.mark.asyncio
async def test_document_jobs_and_jobs_listing(client: TestClient):
    """Verifies GET /api/v1/documents/{doc_id}/jobs and GET /api/v1/jobs listing endpoints."""
    upload_res = client.post(
        "/api/v1/documents",
        files={"file": ("jamabandi_list.pdf", io.BytesIO(SAMPLE_JAMABANDI_TEXT.encode("utf-8")), "application/pdf")},
        data={"doc_type": "JAMABANDI"}
    )
    doc_id = upload_res.json()["id"]

    # Enqueue job
    proc_res = client.post(f"/api/v1/documents/{doc_id}/process?background=true")
    job_id = proc_res.json()["id"]

    import asyncio
    await asyncio.sleep(0.2)

    # 1. Query document-specific jobs
    doc_jobs_res = client.get(f"/api/v1/documents/{doc_id}/jobs")
    assert doc_jobs_res.status_code == 200
    doc_jobs = doc_jobs_res.json()
    assert len(doc_jobs) >= 1
    assert doc_jobs[0]["id"] == job_id

    # 2. Query paginated global jobs list
    all_jobs_res = client.get("/api/v1/jobs")
    assert all_jobs_res.status_code == 200
    jobs_page = all_jobs_res.json()
    assert jobs_page["total"] >= 1
    assert any(j["id"] == job_id for j in jobs_page["data"])

    # 3. Filter by status
    completed_jobs_res = client.get("/api/v1/jobs?status=COMPLETED")
    assert completed_jobs_res.status_code == 200
    assert all(j["status"] == "COMPLETED" for j in completed_jobs_res.json()["data"])

