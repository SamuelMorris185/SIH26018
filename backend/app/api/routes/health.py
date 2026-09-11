from datetime import datetime, timezone
from fastapi import APIRouter
from app.core.config import settings
from app.schemas.health import HealthCheckResponse, ServicesHealth

router = APIRouter()

@router.get("/health", response_model=HealthCheckResponse, tags=["Diagnostics"])
async def get_health():
    """
    Health check endpoint returning backend status and environmental details.
    """
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        environment=settings.APP_ENV,
        services=ServicesHealth(
            backend="ok",
            database="configured"
        )
    )
