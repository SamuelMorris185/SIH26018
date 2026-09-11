import uuid
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, create_access_token
from app.models.user import UserModel
from app.models.document import DocumentModel

def setup_users(session: AsyncSession):
    admin = UserModel(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        email="admin@sih.gov.in",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Administrator",
        role="ADMIN",
        is_active=True,
        created_at=datetime.utcnow()
    )
    operator_a = UserModel(
        id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        email="operator_a@sih.gov.in",
        hashed_password=get_password_hash("OperatorPass123!"),
        full_name="Operator A",
        role="OPERATOR",
        is_active=True,
        created_at=datetime.utcnow()
    )
    operator_b = UserModel(
        id=uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
        email="operator_b@sih.gov.in",
        hashed_password=get_password_hash("OperatorPass123!"),
        full_name="Operator B",
        role="OPERATOR",
        is_active=True,
        created_at=datetime.utcnow()
    )
    reviewer = UserModel(
        id=uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
        email="reviewer@sih.gov.in",
        hashed_password=get_password_hash("ReviewerPass123!"),
        full_name="Reviewer User",
        role="REVIEWER",
        is_active=True,
        created_at=datetime.utcnow()
    )
    viewer = UserModel(
        id=uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
        email="viewer@sih.gov.in",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Viewer User",
        role="VIEWER",
        is_active=True,
        created_at=datetime.utcnow()
    )
    inactive = UserModel(
        id=uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
        email="inactive@sih.gov.in",
        hashed_password=get_password_hash("InactivePass123!"),
        full_name="Inactive User",
        role="OPERATOR",
        is_active=False,
        created_at=datetime.utcnow()
    )
    return [admin, operator_a, operator_b, reviewer, viewer, inactive]

@pytest.mark.anyio
async def test_auth_login_endpoints(unauthenticated_client: TestClient, db_session: AsyncSession):
    users = setup_users(db_session)
    db_session.add_all(users)
    await db_session.commit()

    # 1. Successful Login
    res = unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sih.gov.in", "password": "AdminPass123!"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "admin@sih.gov.in"
    assert data["user"]["role"] == "ADMIN"
    assert "password" not in data["user"]
    assert "hashed_password" not in data["user"]

    token = data["access_token"]

    # 2. Invalid Password -> 401 with generic message
    bad_pass = unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sih.gov.in", "password": "WrongPassword!"}
    )
    assert bad_pass.status_code == 401
    assert "Invalid email or password" in bad_pass.json()["message"]

    # 3. Nonexistent User -> 401 with identical generic message
    unknown_user = unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@sih.gov.in", "password": "AnyPassword123!"}
    )
    assert unknown_user.status_code == 401
    assert "Invalid email or password" in unknown_user.json()["message"]

    # 4. Deactivated User -> 401
    inactive_res = unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@sih.gov.in", "password": "InactivePass123!"}
    )
    assert inactive_res.status_code == 401
    assert "deactivated" in inactive_res.json()["message"].lower()

    # 5. GET /api/v1/auth/me with valid token
    me_res = unauthenticated_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == "admin@sih.gov.in"
    assert me_data["role"] == "ADMIN"
    assert "password" not in me_data

    # 6. GET /api/v1/auth/me without token -> 401
    no_token_res = unauthenticated_client.get("/api/v1/auth/me")
    assert no_token_res.status_code == 401
    assert "WWW-Authenticate" in no_token_res.headers

@pytest.mark.anyio
async def test_rbac_admin_user_management(unauthenticated_client: TestClient, db_session: AsyncSession):
    users = setup_users(db_session)
    db_session.add_all(users)
    await db_session.commit()

    admin_token = create_access_token({"sub": str(users[0].id), "role": users[0].role})
    operator_token = create_access_token({"sub": str(users[1].id), "role": users[1].role})
    viewer_token = create_access_token({"sub": str(users[4].id), "role": users[4].role})

    # 1. Admin can create new user
    create_res = unauthenticated_client.post(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": "new.patwari@sih.gov.in",
            "full_name": "New Patwari",
            "role": "OPERATOR",
            "password": "PatwariSecure123!"
        }
    )
    assert create_res.status_code == 201
    new_user_id = create_res.json()["id"]

    # 2. Operator CANNOT create new user -> 403 Forbidden
    op_create = unauthenticated_client.post(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "email": "should_fail@sih.gov.in",
            "full_name": "Fail User",
            "role": "VIEWER",
            "password": "Password123!"
        }
    )
    assert op_create.status_code == 403

    # 3. Viewer CANNOT create new user -> 403 Forbidden
    vw_create = unauthenticated_client.post(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={
            "email": "should_fail2@sih.gov.in",
            "full_name": "Fail User 2",
            "role": "VIEWER",
            "password": "Password123!"
        }
    )
    assert vw_create.status_code == 403

    # 4. Admin can list users
    list_res = unauthenticated_client.get(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 6

    # 5. Operator CANNOT list users -> 403
    op_list = unauthenticated_client.get(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    assert op_list.status_code == 403

@pytest.mark.anyio
async def test_resource_ownership_and_role_restrictions(unauthenticated_client: TestClient, db_session: AsyncSession):
    users = setup_users(db_session)
    db_session.add_all(users)
    await db_session.commit()

    admin_token = create_access_token({"sub": str(users[0].id), "role": users[0].role})
    op_a_token = create_access_token({"sub": str(users[1].id), "role": users[1].role})
    op_b_token = create_access_token({"sub": str(users[2].id), "role": users[2].role})
    viewer_token = create_access_token({"sub": str(users[4].id), "role": users[4].role})

    # 1. Viewer CANNOT upload documents -> 403 Forbidden
    vw_upload = unauthenticated_client.post(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {viewer_token}"},
        files={"file": ("viewer_test.pdf", b"%PDF-1.4 sample content", "application/pdf")},
        data={"doc_type": "JAMABANDI"}
    )
    assert vw_upload.status_code == 403

    # 2. Operator A uploads a document -> 201 Created
    op_a_upload = unauthenticated_client.post(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {op_a_token}"},
        files={"file": ("operator_a_record.pdf", b"%PDF-1.4 sample content", "application/pdf")},
        data={"doc_type": "JAMABANDI"}
    )
    assert op_a_upload.status_code == 201
    doc_id = op_a_upload.json()["id"]
    assert op_a_upload.json()["created_by"] == str(users[1].id)

    # 3. Operator B CANNOT access Operator A's document -> 403 Forbidden
    op_b_access = unauthenticated_client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {op_b_token}"}
    )
    assert op_b_access.status_code == 403

    # 4. Operator B CANNOT process Operator A's document -> 403 Forbidden
    op_b_process = unauthenticated_client.post(
        f"/api/v1/documents/{doc_id}/process",
        headers={"Authorization": f"Bearer {op_b_token}"}
    )
    assert op_b_process.status_code == 403

    # 5. Operator A CAN access own document -> 200 OK
    op_a_access = unauthenticated_client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {op_a_token}"}
    )
    assert op_a_access.status_code == 200

    # 6. Admin CAN access Operator A's document -> 200 OK
    admin_access = unauthenticated_client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert admin_access.status_code == 200
