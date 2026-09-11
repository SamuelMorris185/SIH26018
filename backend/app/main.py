from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging, logger
from sqlalchemy.exc import SQLAlchemyError
from app.core.exceptions import DomainException, domain_exception_handler, database_exception_handler
from app.api.router import api_router
from app.schemas.health import HealthCheckResponse, ServicesHealth, RootResponse

# Initialize logging
setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    description="FastAPI Backend for SIH26018 Intelligent Land Record Digitization and Validation System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Register exception handlers
app.add_exception_handler(DomainException, domain_exception_handler)
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(OSError, database_exception_handler)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API V1 router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", response_model=RootResponse, tags=["Root"])
async def root():
    """
    Root API health and system information endpoint.
    """
    return RootResponse(
        name=settings.APP_NAME,
        version="1.0.0",
        status="online"
    )

@app.get("/health", response_model=HealthCheckResponse, tags=["Diagnostics"])
async def health():
    """
    Global root health check endpoint for monitoring and frontend integration.
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
