import io
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import get_password_hash, create_access_token
from app.models.user import UserModel
from app.models.audit_log import AuditLogModel
from tests.fixtures.sample_documents.manifest import SAMPLE_FIXTURES

def create_operator_user():
    return UserModel(
        id=uuid.UUID("11111111-9999-8888-7777-666666666666"),
        email="operator_pipeline@sih.gov.in",
        hashed_password=get_password_hash("OpPass123!"),
        full_name="Pipeline Operator",
        role="OPERATOR",
        is_active=True
    )

@pytest.mark.anyio
async def test_end_to_end_phase5_pipeline_with_discrepancy_detection(
    unauthenticated_client: TestClient,
    db_session: AsyncSession
):
    operator = create_operator_user()
    db_session.add(operator)
    await db_session.commit()
    token = create_access_token({"sub": str(operator.id), "role": operator.role})
    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Upload & Process Clean Baseline Document
    f_clean = SAMPLE_FIXTURES["clean_record"]
    res1 = unauthenticated_client.post(
        "/api/v1/digitization/upload-and-process",
        files={"file": (f_clean["file_name"], io.BytesIO(f_clean["content"]), "application/pdf")},
        data={"doc_type": f_clean["doc_type"]},
        headers=headers
    )
    assert res1.status_code == 201, res1.text
    data1 = res1.json()
    assert data1["document"]["status"] == "VALIDATED"
    assert len(data1["records"]) == 1
    rec1 = data1["records"][0]
    assert rec1["owner_name"] == "Ram Prasad Sharma"
    assert rec1["status"] == "VALIDATED"
    assert data1["discrepancies"]["total_discrepancies"] == 0

    # Step 2: Upload & Process Conflicting Owner Document
    f_owner = SAMPLE_FIXTURES["owner_mismatch"]
    res2 = unauthenticated_client.post(
        "/api/v1/digitization/upload-and-process",
        files={"file": (f_owner["file_name"], io.BytesIO(f_owner["content"]), "application/pdf")},
        data={"doc_type": f_owner["doc_type"]},
        headers=headers
    )
    assert res2.status_code == 201, res2.text
    data2 = res2.json()
    assert data2["document"]["status"] == "FLAGGED"
    rec2 = data2["records"][0]
    assert rec2["owner_name"] == "Vikram Aditya Singh"
    assert rec2["status"] == "FLAGGED"
    assert data2["discrepancies"]["total_discrepancies"] >= 1
    types2 = [d["discrepancy_type"] for d in data2["discrepancies"]["discrepancies"]]
    assert "OWNER_MISMATCH" in types2

    # Verify audit event logged for discrepancy detection
    audit_res = await db_session.execute(
        select(AuditLogModel).where(AuditLogModel.action == "DISCREPANCIES_DETECTED")
    )
    audit_logs = audit_res.scalars().all()
    assert len(audit_logs) >= 1

    # Step 3: Upload & Process Conflicting Area Document
    f_area = SAMPLE_FIXTURES["area_mismatch"]
    res3 = unauthenticated_client.post(
        "/api/v1/digitization/upload-and-process",
        files={"file": (f_area["file_name"], io.BytesIO(f_area["content"]), "application/pdf")},
        data={"doc_type": f_area["doc_type"]},
        headers=headers
    )
    assert res3.status_code == 201, res3.text
    data3 = res3.json()
    assert data3["document"]["status"] == "FLAGGED"
    rec3 = data3["records"][0]
    assert rec3["area_in_hectares"] == 3.7500
    assert rec3["status"] == "FLAGGED"
    types3 = [d["discrepancy_type"] for d in data3["discrepancies"]["discrepancies"]]
    assert "AREA_MISMATCH" in types3

    # Step 4: Verify manual compare endpoint is idempotent across repeated calls
    compare_res1 = unauthenticated_client.post(
        f"/api/v1/records/{rec2['id']}/compare",
        headers=headers
    )
    assert compare_res1.status_code == 200
    summary1 = compare_res1.json()

    compare_res2 = unauthenticated_client.post(
        f"/api/v1/records/{rec2['id']}/compare",
        headers=headers
    )
    assert compare_res2.status_code == 200
    summary2 = compare_res2.json()

    assert summary1["total_discrepancies"] == summary2["total_discrepancies"]
    assert summary1["total_discrepancies"] >= 2
