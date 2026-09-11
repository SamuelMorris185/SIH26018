from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.validation import ValidationCheckResponse
from app.schemas.discrepancy import DiscrepancyResponse

class LandRecordBase(BaseModel):
    state: str = Field(..., json_schema_extra={"example": "Madhya Pradesh"})
    district: str = Field(..., json_schema_extra={"example": "Bhopal"})
    tehsil: str = Field(..., json_schema_extra={"example": "Huzur"})
    village: str = Field(..., json_schema_extra={"example": "Bairagarh"})
    khasra_number: str = Field(..., json_schema_extra={"example": "104/2"})
    khata_number: str = Field(..., json_schema_extra={"example": "45"})
    area_in_hectares: float = Field(..., ge=0.0, json_schema_extra={"example": 1.25})
    land_classification: Optional[str] = Field(default="Agricultural", json_schema_extra={"example": "Agricultural"})
    
    # Phase 5: Structured Ownership & Legal Metadata
    owner_name: Optional[str] = Field(default=None, json_schema_extra={"example": "Ram Prasad Sharma"})
    co_owners: Optional[List[str]] = Field(default=None, json_schema_extra={"example": ["Shyam Prasad Sharma"]})
    patta_number: Optional[str] = Field(default=None, json_schema_extra={"example": "PATTA-2024-889"})
    registration_number: Optional[str] = Field(default=None, json_schema_extra={"example": "REG-2024-MP-00123"})
    mutation_number: Optional[str] = Field(default=None, json_schema_extra={"example": "MUT-2024-00456"})
    document_date: Optional[datetime] = None

class LandRecordCreate(LandRecordBase):
    document_id: Optional[UUID] = None
    created_by: Optional[UUID] = None
    confidence_score: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    status: Optional[str] = Field(default="EXTRACTED")
    review_status: Optional[str] = Field(default="PENDING_REVIEW")

class LandRecordUpdate(BaseModel):
    state: Optional[str] = None
    district: Optional[str] = None
    tehsil: Optional[str] = None
    village: Optional[str] = None
    khasra_number: Optional[str] = None
    khata_number: Optional[str] = None
    area_in_hectares: Optional[float] = Field(default=None, ge=0.0)
    land_classification: Optional[str] = None
    owner_name: Optional[str] = None
    co_owners: Optional[List[str]] = None
    patta_number: Optional[str] = None
    registration_number: Optional[str] = None
    mutation_number: Optional[str] = None
    document_date: Optional[datetime] = None
    status: Optional[str] = None
    review_status: Optional[str] = None

class LandRecordResponse(LandRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: Optional[UUID] = None
    created_by: Optional[UUID] = None
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    status: str = Field(default="EXTRACTED", json_schema_extra={"example": "VALIDATED"})
    review_status: str = Field(default="PENDING_REVIEW", json_schema_extra={"example": "PENDING_REVIEW"})
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class LandRecordDetailResponse(LandRecordResponse):
    latest_validation: Optional[ValidationCheckResponse] = None
    discrepancies: Optional[List[DiscrepancyResponse]] = Field(default_factory=list)

class LandRecordPaginatedList(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: Optional[int] = None
    data: List[LandRecordResponse]
