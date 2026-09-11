import uuid
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, create_access_token
from app.models.user import UserModel
from app.models.land_record import LandRecordModel

def create_governance_users(session: AsyncSession):
    admin = UserModel(
        id=uuid.UUID("11111111-2222-3333-4444-555555555555"),
        email="admin_gov@sih.gov.in",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Gov Admin",
        role="ADMIN",
        is_active=True,
        created_at=datetime.utcnow()
    )
    operator = UserModel(
        id=uuid.UUID("22222222-3333-4444-5555-666666666666"),
        email="operator_gov@sih.gov.in",
        hashed_password=get_password_hash("OperatorPass123!"),
        full_name="Gov Operator",
        role="OPERATOR",
        is_active=True,
        created_at=datetime.utcnow()
    )
    reviewer = UserModel(
        id=uuid.UUID("33333333-4444-5555-6666-777777777777"),
        email="reviewer_gov@sih.gov.in",
        hashed_password=get_password_hash("ReviewerPass123!"),
        full_name="Gov Reviewer",
        role="REVIEWER",
        is_active=True,
        created_at=datetime.utcnow()
    )
    viewer = UserModel(
        id=uuid.UUID("44444444-5555-6666-7777-888888888888"),
        email="viewer_gov@sih.gov.in",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Gov Viewer",
        role="VIEWER",
        is_active=True,
        created_at=datetime.utcnow()
    )
    return admin, operator, reviewer, viewer

@pytest.mark.anyio
async def test_human_review_endpoints_workflow(unauthenticated_client: TestClient, db_session: AsyncSession):
    admin, operator, reviewer, viewer = create_governance_users(db_session)
    db_session.add_all([admin, operator, reviewer, viewer])

    record = LandRecordModel(
        id=uuid.uuid4(),
        state="Rajasthan",
        district="Jaipur",
        tehsil="Amer",
        village="Kukas",
        khasra_number="502/1",
        khata_number="88",
        area_in_hectares=3.15,
        land_classification="Agricultural",
        confidence_score=0.88,
        status="FLAGGED",
        review_status="PENDING_REVIEW",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(record)
    await db_session.commit()

    admin_token = create_access_token({"sub": str(admin.id), "role": admin.role})
    op_token = create_access_token({"sub": str(operator.id), "role": operator.role})
    rev_token = create_access_token({"sub": str(reviewer.id), "role": reviewer.role})
    view_token = create_access_token({"sub": str(viewer.id), "role": viewer.role})

    # 1. Inspect initial review state (Viewer can view)
    get_res = unauthenticated_client.get(
        f"/api/v1/records/{record.id}/review",
        headers={"Authorization": f"Bearer {view_token}"}
    )
    assert get_res.status_code == 200
    assert get_res.json()["review_status"] == "PENDING_REVIEW"

    # 2. Operator CANNOT approve -> 403 Forbidden
    op_app = unauthenticated_client.post(
        f"/api/v1/records/{record.id}/approve",
        headers={"Authorization": f"Bearer {op_token}"},
        json={"notes": "Looks fine to me"}
    )
    assert op_app.status_code == 403

    # 3. Viewer CANNOT approve -> 403 Forbidden
    vw_app = unauthenticated_client.post(
        f"/api/v1/records/{record.id}/approve",
        headers={"Authorization": f"Bearer {view_token}"},
        json={"notes": "Looks fine"}
    )
    assert vw_app.status_code == 403

    # 4. Operator submits for review -> 200 OK (transitions to IN_REVIEW)
    submit_res = unauthenticated_client.post(
        f"/api/v1/records/{record.id}/submit-review",
        headers={"Authorization": f"Bearer {op_token}"},
        json={"notes": "Submitted due to low optical confidence on parcel index"}
    )
    assert submit_res.status_code == 200
    assert submit_res.json()["review_status"] == "IN_REVIEW"

    # 5. Reviewer rejects WITHOUT explanation (< 5 chars) -> 422 Unprocessable
    bad_rej = unauthenticated_client.post(
        f"/api/v1/records/{record.id}/reject",
        headers={"Authorization": f"Bearer {rev_token}"},
        json={"rejection_reason": "no"}
    )
    assert bad_rej.status_code == 422

    # 6. Reviewer rejects WITH mandatory explanation -> 200 OK
    good_rej = unauthenticated_client.post(
        f"/api/v1/records/{record.id}/reject",
        headers={"Authorization": f"Bearer {rev_token}"},
        json={
            "rejection_reason": "Khasra number 502/1 does not match cadastral village map grid for Kukas.",
            "notes": "Physical resurvey required by tehsildar."
        }
    )
    assert good_rej.status_code == 200
    assert good_rej.json()["review_status"] == "REJECTED"
    assert "Khasra number 502/1" in good_rej.json()["rejection_reason"]

    # 7. Create a second record to test successful Reviewer Approval
    record_2 = LandRecordModel(
        id=uuid.uuid4(),
        state="Rajasthan",
        district="Jaipur",
        tehsil="Amer",
        village="Kukas",
        khasra_number="503",
        khata_number="89",
        area_in_hectares=1.20,
        land_classification="Agricultural",
        confidence_score=0.98,
        status="VALIDATED",
        review_status="PENDING_REVIEW",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(record_2)
    await db_session.commit()

    # Reviewer approves record_2 -> 200 OK
    app_res = unauthenticated_client.post(
        f"/api/v1/records/{record_2.id}/approve",
        headers={"Authorization": f"Bearer {rev_token}"},
        json={"notes": "Verified against physical registry volume 14 page 88."}
    )
    assert app_res.status_code == 200
    assert app_res.json()["review_status"] == "APPROVED"
    assert app_res.json()["reviewed_by"] == str(reviewer.id)

@pytest.mark.anyio
async def test_audit_logs_endpoints(unauthenticated_client: TestClient, db_session: AsyncSession):
    admin, operator, reviewer, viewer = create_governance_users(db_session)
    db_session.add_all([admin, operator, reviewer, viewer])
    await db_session.commit()

    admin_token = create_access_token({"sub": str(admin.id), "role": admin.role})
    op_token = create_access_token({"sub": str(operator.id), "role": operator.role})

    # 1. Unauthenticated user CANNOT access audit logs -> 401
    no_auth = unauthenticated_client.get("/api/v1/audit-logs")
    assert no_auth.status_code == 401

    # 2. Operator CANNOT access audit logs -> 403 Forbidden
    op_res = unauthenticated_client.get(
        "/api/v1/audit-logs",
        headers={"Authorization": f"Bearer {op_token}"}
    )
    assert op_res.status_code == 403

    # 3. Admin CAN access audit logs -> 200 OK
    admin_res = unauthenticated_client.get(
        "/api/v1/audit-logs",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert admin_res.status_code == 200
    data = admin_res.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)
