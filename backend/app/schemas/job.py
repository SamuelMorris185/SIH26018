import uuid
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field

class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"

class JobStage(str, Enum):
    QUEUED = "QUEUED"
    STORAGE_READ = "STORAGE_READ"
    OCR_EXTRACTION = "OCR_EXTRACTION"
    NORMALIZATION = "NORMALIZATION"
    RECORD_UPSERT = "RECORD_UPSERT"
    VALIDATION = "VALIDATION"
    DISCREPANCY_DETECTION = "DISCREPANCY_DETECTION"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class JobErrorCategory(str, Enum):
    EXTRACTION_ERROR = "EXTRACTION_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    STORAGE_ERROR = "STORAGE_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"

class JobResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    created_by: Optional[uuid.UUID] = None
    status: JobStatus
    current_stage: str
    progress_percentage: int = Field(ge=0, le=100)
    error_category: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = Field(default=0, ge=0)
    max_retries: int = Field(default=3, ge=1)
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result_summary: Optional[Dict[str, Any]] = None
    metadata_json: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class JobPaginatedList(BaseModel):
    total: int
    page: int
    limit: int
    data: List[JobResponse]

class JobRetryRequest(BaseModel):
    force: Optional[bool] = False
