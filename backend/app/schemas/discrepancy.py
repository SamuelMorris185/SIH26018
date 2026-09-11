from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

class DiscrepancyType(str, Enum):
    OWNER_MISMATCH = "OWNER_MISMATCH"
    CO_OWNER_MISMATCH = "CO_OWNER_MISMATCH"
    AREA_MISMATCH = "AREA_MISMATCH"
    SURVEY_CONFLICT = "SURVEY_CONFLICT"
    LOCATION_MISMATCH = "LOCATION_MISMATCH"
    IDENTIFIER_CONFLICT = "IDENTIFIER_CONFLICT"
    DUPLICATE_DOCUMENT = "DUPLICATE_DOCUMENT"
    SUSPICIOUS_DATE_SEQUENCE = "SUSPICIOUS_DATE_SEQUENCE"
    MISSING_RELATED_RECORD = "MISSING_RELATED_RECORD"
    LOW_CONFIDENCE_CRITICAL_FIELD = "LOW_CONFIDENCE_CRITICAL_FIELD"

class DiscrepancySeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class DiscrepancyStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"

class DiscrepancyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    record_id: UUID
    compared_record_id: Optional[UUID] = None
    comparison_id: Optional[UUID] = None
    discrepancy_type: str
    severity: str
    description: str
    field_name: Optional[str] = None
    source_value: Optional[str] = None
    conflicting_value: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    status: str = Field(default="OPEN")
    created_at: datetime
    updated_at: datetime

class DiscrepancyUpdate(BaseModel):
    status: DiscrepancyStatus
    resolution_notes: Optional[str] = None

class RecordComparisonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    record_id: UUID
    compared_record_id: UUID
    match_type: str
    discrepancy_count: int
    highest_severity: Optional[str] = None
    status: str
    compared_at: datetime
    discrepancies: List[DiscrepancyResponse] = Field(default_factory=list)

class ComparisonSummaryResponse(BaseModel):
    record_id: UUID
    matched_records_count: int
    total_discrepancies: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    highest_severity: Optional[str] = None
    discrepancies: List[DiscrepancyResponse]

class DiscrepancyPaginatedList(BaseModel):
    total: int
    page: int
    limit: int
    data: List[DiscrepancyResponse]

