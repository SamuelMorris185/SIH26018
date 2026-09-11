import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_get_ocr_status_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/system/ocr-status")
        assert response.status_code == 200
        data = response.json()

        assert "selected_engine" in data
        assert "available" in data
        assert "provider_name" in data
        assert "engine_version" in data
        assert "supported_languages" in data
        assert "offline_operational" in data

        # Check safety: no system paths leaked
        data_str = str(data).lower()
        assert "c:\\" not in data_str
        assert "/users/" not in data_str
        assert "password" not in data_str
        assert "secret" not in data_str
