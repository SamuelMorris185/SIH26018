from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field

class ServicesHealth(BaseModel):
    backend: str = Field(default="ok", json_schema_extra={"example": "ok"})
    database: str = Field(default="configured", json_schema_extra={"example": "connected"})

class HealthCheckResponse(BaseModel):
    status: str = Field(default="healthy", json_schema_extra={"example": "healthy"})
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    environment: str = Field(..., json_schema_extra={"example": "development"})
    services: ServicesHealth

class RootResponse(BaseModel):
    name: str
    version: str
    status: str

class OCRStatusResponse(BaseModel):
    selected_engine: str = Field(..., json_schema_extra={"example": "TESSERACT"})
    available: bool = Field(..., json_schema_extra={"example": True})
    provider_name: str = Field(..., json_schema_extra={"example": "TESSERACT_OCR_V1"})
    engine_version: Optional[str] = Field(None, json_schema_extra={"example": "5.5.3"})
    supported_languages: List[str] = Field(default_factory=list, json_schema_extra={"example": ["eng", "hin", "osd"]})
    offline_operational: bool = Field(default=True, json_schema_extra={"example": True})

class DashboardStatsResponse(BaseModel):
    total_records: int = Field(default=0)
    documents_processed: int = Field(default=0)
    records_awaiting_review: int = Field(default=0)
    validated_records: int = Field(default=0)
    flagged_records: int = Field(default=0)
    open_discrepancies: int = Field(default=0)
    low_confidence_records: int = Field(default=0)
    approved_records: int = Field(default=0)
    rejected_records: int = Field(default=0)

