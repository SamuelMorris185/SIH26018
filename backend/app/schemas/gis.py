import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field

class ParcelLocationBase(BaseModel):
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    boundary_geojson: Optional[Dict[str, Any]] = None
    coordinate_reference_system: str = Field(default="EPSG:4326")
    map_source: str = Field(default="CADASTRAL_SURVEY")
    location_confidence: float = Field(default=1.0, ge=0.0, le=1.0)

class ParcelLocationCreate(ParcelLocationBase):
    record_id: uuid.UUID

class ParcelLocationUpdate(BaseModel):
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    boundary_geojson: Optional[Dict[str, Any]] = None
    geometry_validation_status: Optional[str] = None
    map_source: Optional[str] = None
    location_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

class ParcelLocationResponse(ParcelLocationBase):
    id: uuid.UUID
    record_id: uuid.UUID
    geometry_validation_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CadastralMapRecord(BaseModel):
    """
    Optimized and sanitized GIS payload for map visualization.
    Only exposes non-sensitive spatial features and operational identifiers.
    """
    record_id: uuid.UUID
    khasra_number: str
    khata_number: str
    state: str
    district: str
    tehsil: str
    village: str
    area_in_hectares: float
    land_classification: Optional[str] = None
    status: str
    review_status: str
    confidence_score: float
    has_discrepancies: bool = False
    discrepancy_count: int = 0
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    boundary_geojson: Optional[Dict[str, Any]] = None
    geometry_validation_status: str = "VALID"
    map_source: str = "CADASTRAL_SURVEY"

    model_config = ConfigDict(from_attributes=True)

class CadastralMapResponse(BaseModel):
    total_parcels: int
    parcels: List[CadastralMapRecord]

class GeometryValidationRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    boundary_geojson: Optional[Dict[str, Any]] = None
    coordinate_reference_system: Optional[str] = "EPSG:4326"

class GeometryValidationResponse(BaseModel):
    is_valid: bool
    geometry_type: Optional[str] = None
    vertex_count: Optional[int] = None
    coordinate_reference_system: str = "EPSG:4326"
    errors: List[str] = []
    warnings: List[str] = []
