from pathlib import Path
from typing import List, Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

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
    OCR_LANGUAGES: str = "eng+hin+tam"
    OCR_TIMEOUT_SECONDS: int = 20
    OCR_DOCUMENT_TIMEOUT_SECONDS: int = 120
    OCR_MAX_PIXELS: int = 24_000_000
    OCR_MAX_PAGES: int = 8
    OCR_MAX_PASSES: int = 3
    CONFIDENCE_THRESHOLD_HIGH: float = 0.85
    CONFIDENCE_THRESHOLD_MEDIUM: float = 0.60
    CONFIDENCE_THRESHOLD_LOW: float = 0.60
    AREA_TOLERANCE_HECTARES: float = 0.01

    # Phase 9: AI Intelligence Layer (Gemini Assistance)
    AI_ENABLED: bool = False
    AI_PROVIDER: str = "gemini"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.8-flash"
    AI_TIMEOUT_SECONDS: int = 30

    @model_validator(mode="after")
    def validate_configuration(self):
        self.OCR_ENGINE = self.OCR_ENGINE.strip().upper()
        self.AI_PROVIDER = self.AI_PROVIDER.strip().lower()
        if self.AI_TIMEOUT_SECONDS <= 0:
            raise ValueError("AI_TIMEOUT_SECONDS must be positive")
        if not 1 <= self.OCR_MAX_PASSES <= 4 or not 1 <= self.OCR_MAX_PAGES <= 20:
            raise ValueError('OCR pass/page limits must be bounded')
        if min(self.OCR_MAX_PIXELS, self.OCR_TIMEOUT_SECONDS, self.OCR_DOCUMENT_TIMEOUT_SECONDS) <= 0:
            raise ValueError('OCR analysis limits must be positive')
        if self.OCR_ENGINE not in {"MOCK", "TESSERACT"}:
            raise ValueError("OCR_ENGINE must be MOCK or TESSERACT")
        if self.APP_ENV.lower() not in {"development", "test", "testing"}:
            if self.JWT_SECRET_KEY.startswith("dev_") or len(self.JWT_SECRET_KEY.encode()) < 32:
                raise ValueError("Set a unique JWT_SECRET_KEY of at least 32 bytes outside development")
        if not 0 <= self.CONFIDENCE_THRESHOLD_LOW <= self.CONFIDENCE_THRESHOLD_MEDIUM <= self.CONFIDENCE_THRESHOLD_HIGH <= 1:
            raise ValueError("Confidence thresholds must be ordered within [0, 1]")
        if self.ACCESS_TOKEN_EXPIRE_MINUTES <= 0 or self.MAX_UPLOAD_SIZE_BYTES <= 0:
            raise ValueError("Token lifetime and upload limit must be positive")
        return self

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
