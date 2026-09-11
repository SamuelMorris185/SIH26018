import uuid
import pytest
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token
)
from app.core.exceptions import (
    AuthenticationError,
    UserAlreadyExistsError,
    UserNotFoundError
)
from app.schemas.user import UserCreate, UserRole, UserUpdate
from app.services.user_service import UserService
from app.services.audit_service import AuditService

@pytest.mark.anyio
async def test_password_hashing_and_salting():
    plain = "SecureRevenuePass#2026"
    hash1 = get_password_hash(plain)
    hash2 = get_password_hash(plain)

    # Different salts produce different hashes
    assert hash1 != hash2
    assert hash1 != plain
    assert "$2b$" in hash1

    assert verify_password(plain, hash1) is True
    assert verify_password(plain, hash2) is True
    assert verify_password("WrongPassword123", hash1) is False

@pytest.mark.anyio
async def test_jwt_token_generation_and_validation():
    user_id = str(uuid.uuid4())
    token = create_access_token({"sub": user_id, "role": "OPERATOR"})

    payload = decode_access_token(token)
    assert payload["sub"] == user_id
    assert payload["role"] == "OPERATOR"
    assert "exp" in payload
    assert "iat" in payload

@pytest.mark.anyio
async def test_jwt_expired_token_rejection():
    user_id = str(uuid.uuid4())
    # Create token expired 10 seconds ago
    expired_token = create_access_token(
        {"sub": user_id, "role": "VIEWER"},
        expires_delta=timedelta(seconds=-10)
    )

    with pytest.raises(AuthenticationError) as exc_info:
        decode_access_token(expired_token)
    assert "expired" in exc_info.value.message.lower()

@pytest.mark.anyio
async def test_jwt_malformed_token_rejection():
    with pytest.raises(AuthenticationError) as exc_info:
        decode_access_token("this.is.not.a.valid.jwt.token")
    assert "invalid or malformed" in exc_info.value.message.lower()

@pytest.mark.anyio
async def test_user_service_crud_and_auth(db_session: AsyncSession):
    service = UserService()

    # 1. Create User
    create_dto = UserCreate(
        email="rajesh.patel@mp.gov.in",
        full_name="Rajesh Patel",
        role=UserRole.OPERATOR,
        password="ValidPassword123!"
    )
    user = await service.create_user(db_session, create_dto)
    assert user.id is not None
    assert user.email == "rajesh.patel@mp.gov.in"
    assert user.role == "OPERATOR"
    assert user.is_active is True
    assert user.hashed_password != "ValidPassword123!"

    # 2. Duplicate email rejection
    with pytest.raises(UserAlreadyExistsError):
        await service.create_user(db_session, create_dto)

    # 3. Successful Authentication
    authenticated = await service.authenticate(db_session, "rajesh.patel@mp.gov.in", "ValidPassword123!")
    assert authenticated.id == user.id

    # 4. Invalid Password Authentication Failure
    with pytest.raises(AuthenticationError):
        await service.authenticate(db_session, "rajesh.patel@mp.gov.in", "WrongPassword!")

    # 5. Unknown User Authentication Failure
    with pytest.raises(AuthenticationError):
        await service.authenticate(db_session, "nonexistent@mp.gov.in", "AnyPassword123!")

    # 6. Deactivated User Authentication Failure
    await service.update_user(db_session, user.id, UserUpdate(is_active=False))
    with pytest.raises(AuthenticationError) as exc_info:
        await service.authenticate(db_session, "rajesh.patel@mp.gov.in", "ValidPassword123!")
    assert "deactivated" in exc_info.value.message.lower()

@pytest.mark.anyio
async def test_audit_service_append_only(db_session: AsyncSession):
    service = AuditService()
    actor_id = uuid.uuid4()
    target_id = uuid.uuid4()

    # Log event with sensitive metadata that should be sanitized
    log_entry = await service.log_event(
        session=db_session,
        action="LOGIN_SUCCESS",
        entity_type="USER",
        actor_user_id=actor_id,
        entity_id=target_id,
        metadata={"password": "secret_password", "district": "Sehore"}
    )
    assert log_entry.id is not None
    assert log_entry.action == "LOGIN_SUCCESS"
    assert log_entry.metadata_json["password"] == "***"
    assert log_entry.metadata_json["district"] == "Sehore"

    # Query audit logs
    total, items = service_logs = await service.list_logs(
        session=db_session,
        action="LOGIN_SUCCESS"
    )
    assert total >= 1
    assert any(item.id == log_entry.id for item in items)
