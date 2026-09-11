import os
import uuid
import shutil
import tempfile
import pytest
from datetime import datetime
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

import app.models
from app.db.base import Base
from app.db.session import get_db_session
from app.main import app as fastapi_app
from app.models.user import UserModel
from app.core.security import get_password_hash, create_access_token
from app.api.dependencies.auth import get_current_user
from app.services.storage_service import LocalStorageService, storage_service
from app.services.digitization_service import digitization_service
from app.services.document_service import document_service

from sqlalchemy.pool import StaticPool

TEST_DB_URL = "sqlite+aiosqlite:///file:sih_test_memdb?mode=memory&cache=shared&uri=true"

test_engine = create_async_engine(
    TEST_DB_URL,
    echo=False,
    future=True,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False, "timeout": 30}
)




TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

DEFAULT_TEST_ADMIN = UserModel(
    id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
    email="testadmin@sih26018.gov.in",
    hashed_password=get_password_hash("AdminPass123!"),
    full_name="Default Test Admin",
    role="ADMIN",
    is_active=True,
    created_at=datetime.utcnow()
)

@pytest.fixture(scope="session", autouse=True)
def configure_test_storage():
    """Sets up a temporary storage directory for documents created during tests."""
    temp_dir = tempfile.mkdtemp(prefix="sih_test_uploads_")
    test_storage = LocalStorageService(base_dir=temp_dir)
    storage_service.base_dir = test_storage.base_dir
    document_service.storage = test_storage
    digitization_service.storage = test_storage
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture(autouse=True)
async def init_db():
    """Initializes a fresh schema before each test and drops it after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides an isolated database session for unit tests."""
    async with TestAsyncSessionLocal() as session:
        yield session

@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient with overridden database session and default admin auth."""
    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with TestAsyncSessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()

    async def override_get_current_user() -> UserModel:
        return DEFAULT_TEST_ADMIN

    fastapi_app.dependency_overrides[get_db_session] = override_get_db_session
    fastapi_app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.dependency_overrides.clear()

@pytest.fixture
def unauthenticated_client() -> TestClient:
    """FastAPI TestClient with overridden database session but NO auth override."""
    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with TestAsyncSessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()

    fastapi_app.dependency_overrides[get_db_session] = override_get_db_session
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.dependency_overrides.clear()

@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async httpx client for full async integration tests."""
    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with TestAsyncSessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()

    async def override_get_current_user() -> UserModel:
        return DEFAULT_TEST_ADMIN

    fastapi_app.dependency_overrides[get_db_session] = override_get_db_session
    fastapi_app.dependency_overrides[get_current_user] = override_get_current_user
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()

@pytest.fixture
def make_auth_headers():
    def _make(user: UserModel) -> dict:
        token = create_access_token({"sub": str(user.id), "role": user.role})
        return {"Authorization": f"Bearer {token}"}
    return _make
