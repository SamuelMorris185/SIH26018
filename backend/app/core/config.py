import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "SIH26018 Intelligent Land Record System"
    APP_ENV: str = "development"
    API_V1_STR: str = "/api/v1"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/sih26018_db"
    FRONTEND_URL: str = "http://localhost:5173"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_MIME_TYPES: List[str] = [
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/tiff",
        "application/octet-stream"
    ]
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"]
    
    # Authentication & Security
    JWT_SECRET_KEY: str = "dev_sih26018_secret_key_change_in_production_min32bytes"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Phase 5: OCR Engine & Confidence Thresholds
    OCR_ENGINE: str = "MOCK"  # "MOCK" or "TESSERACT"
    TESSERACT_CMD_PATH: Optional[str] = None
    CONFIDENCE_THRESHOLD_HIGH: float = 0.85
    CONFIDENCE_THRESHOLD_MEDIUM: float = 0.60
    CONFIDENCE_THRESHOLD_LOW: float = 0.60
    AREA_TOLERANCE_HECTARES: float = 0.01

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
