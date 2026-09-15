import uuid
from app.core.security import create_access_token
from app.models.user import UserModel
from app.services.job_service import job_service


async def test_operator_access_and_review_bypass(unauthenticated_client, db_session):
    client = unauthenticated_client
    users = [UserModel(email=f"audit{i}@example.com", full_name=f"Audit {i}",
                       hashed_password="unused", role=role)
             for i, role in enumerate(["OPERATOR", "OPERATOR", "REVIEWER"])]
    db_session.add_all(users)
    await db_session.commit()
    headers = [{"Authorization": "Bearer " + create_access_token({"sub": str(u.id)})} for u in users]
    upload = client.post("/api/v1/digitization/upload-and-process", headers=headers[0],
                         files={"file": ("low_confidence.pdf", b"mock", "application/pdf")})
    assert upload.status_code == 201, upload.text
    record = upload.json()["records"][0]
    rid = record["id"]
    doc_id = upload.json()["document"]["id"]
    for path in [f"/records/{rid}", f"/records/{rid}/extraction", f"/records/{rid}/validation",
                 f"/records/{rid}/validations", f"/records/{rid}/review", f"/records/{rid}/discrepancies",
                 f"/records/{rid}/comparisons", f"/validation/records/{rid}/history"]:
        response = client.get("/api/v1" + path, headers=headers[1])
        assert response.status_code == 403, (path, response.text)
    for path in ["/records", "/search", "/documents", "/discrepancies"]:
        assert client.get("/api/v1" + path, headers=headers[1]).json()["total"] == 0
    assert client.patch(f"/api/v1/records/{rid}", headers=headers[1], json={"village": "Changed"}).status_code == 403
    for path in [f"/records/{rid}/validate", f"/validation/records/{rid}", f"/records/{rid}/submit-review"]:
        assert client.post("/api/v1" + path, headers=headers[1], json={}).status_code == 403
    assert client.patch(f"/api/v1/records/{rid}", headers=headers[0], json={"review_status": "APPROVED"}).status_code == 403
    assert client.post("/api/v1/records", headers=headers[0], json={**record, "created_by": str(users[1].id)}).status_code == 403
    assert client.post("/api/v1/records", headers=headers[0], json={**record, "review_status": "APPROVED"}).status_code == 403
    assert client.post(f"/api/v1/records/{rid}/approve", headers=headers[2], json={}).status_code == 200
    assert client.post(f"/api/v1/digitization/process/{doc_id}", headers=headers[0]).status_code == 409
    assert client.post(f"/api/v1/records/{rid}/compare", headers=headers[0]).status_code == 409


async def test_retry_dispatch_observes_committed_state(client, db_session, monkeypatch):
    upload = client.post("/api/v1/documents", files={"file": ("retry.pdf", b"test", "application/pdf")})
    job = await job_service.create_job(db_session, uuid.UUID(upload.json()["id"]))
    job.status = "FAILED"
    await db_session.commit()
    observed = []

    def dispatch(job_id):
        # A separate connection must already see QUEUED when dispatch happens.
        import sqlite3
        with sqlite3.connect("file:sih_test_memdb?mode=memory&cache=shared", uri=True) as connection:
            observed.append(connection.execute("SELECT status FROM processing_jobs WHERE id = ?", (job_id.hex,)).fetchone()[0])

    monkeypatch.setattr(job_service, "dispatch_job", dispatch)
    assert client.post(f"/api/v1/jobs/{job.id}/retry").status_code == 202
    assert observed == ["QUEUED"]


def test_deleted_user_token_is_unauthorized(unauthenticated_client):
    token = create_access_token({"sub": str(uuid.uuid4())})
    response = unauthenticated_client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + token})
    assert response.status_code == 401
