from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

class ConfidenceCategory(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

def categorize_confidence(
    confidence: float,
    high_threshold: float = 0.85,
    medium_threshold: float = 0.60
) -> ConfidenceCategory:
    """Categorizes confidence score into HIGH, MEDIUM, or LOW based on thresholds."""
    bounded = max(0.0, min(1.0, float(confidence)))
    if bounded >= high_threshold:
        return ConfidenceCategory.HIGH
    elif bounded >= medium_threshold:
        return ConfidenceCategory.MEDIUM
    return ConfidenceCategory.LOW

class FieldExtractionEvidence(BaseModel):
    """
    Structured extraction metadata for an individual field, containing raw value,
    normalized value, field-level confidence, category, extraction source, and evidence snippet.
    """
    field: str
    value: Any
    normalized_value: Optional[Any] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    category: ConfidenceCategory = ConfidenceCategory.HIGH
    source: str = "ocr"
    evidence: Optional[str] = None

class StructuredLandRecordExtraction(BaseModel):
    """
    Canonical structured land-record extraction schema covering comprehensive field definitions.
    """
    owner_name: Optional[FieldExtractionEvidence] = None
    co_owners: Optional[FieldExtractionEvidence] = None
    khasra_number: Optional[FieldExtractionEvidence] = None
    survey_number: Optional[FieldExtractionEvidence] = None
    khata_number: Optional[FieldExtractionEvidence] = None
    patta_number: Optional[FieldExtractionEvidence] = None
    village: Optional[FieldExtractionEvidence] = None
    tehsil: Optional[FieldExtractionEvidence] = None
    district: Optional[FieldExtractionEvidence] = None
    state: Optional[FieldExtractionEvidence] = None
    area_in_hectares: Optional[FieldExtractionEvidence] = None
    area_unit: Optional[FieldExtractionEvidence] = None
    land_classification: Optional[FieldExtractionEvidence] = None
    registration_number: Optional[FieldExtractionEvidence] = None
    mutation_number: Optional[FieldExtractionEvidence] = None
    document_type: Optional[FieldExtractionEvidence] = None
    document_date: Optional[FieldExtractionEvidence] = None
    registration_date: Optional[FieldExtractionEvidence] = None
    mutation_date: Optional[FieldExtractionEvidence] = None
    source_document_reference: Optional[FieldExtractionEvidence] = None

class ExtractionResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    provider: str = Field(default="MOCK_OCR_V1", json_schema_extra={"example": "MOCK_OCR_V1"})
    raw_text: Optional[str] = None
    extracted_fields: Dict[str, Any]
    field_confidences: Optional[Dict[str, float]] = None
    structured_fields: Optional[Dict[str, FieldExtractionEvidence]] = None
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    confidence_category: ConfidenceCategory = ConfidenceCategory.HIGH
    low_confidence_fields: List[str] = Field(default_factory=list)
    status: str = Field(default="SUCCESS", json_schema_extra={"example": "SUCCESS"})
    extracted_at: datetime

class RawExtractionPayload(BaseModel):
    document_id: UUID
    provider: str = "MOCK_OCR_V1"
    raw_text: Optional[str] = None
    extracted_fields: Dict[str, Any]
    field_confidences: Optional[Dict[str, float]] = None
    structured_fields: Optional[Dict[str, FieldExtractionEvidence]] = None
    confidence_score: float = 1.0
    confidence_category: ConfidenceCategory = ConfidenceCategory.HIGH
    low_confidence_fields: List[str] = Field(default_factory=list)
    status: str = "SUCCESS"
