from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

class DocumentBase(BaseModel):
    file_name: str = Field(..., max_length=255, json_schema_extra={"example": "jamabandi_bhopal_2026.pdf"})
    mime_type: str = Field(..., max_length=100, json_schema_extra={"example": "application/pdf"})
    doc_type: str = Field(default="JAMABANDI", max_length=50, json_schema_extra={"example": "JAMABANDI"})
    metadata_json: Optional[Dict[str, Any]] = Field(default_factory=dict, json_schema_extra={"example": {"district_code": "045", "scan_dpi": 300}})

class DocumentCreate(DocumentBase):
    file_size_bytes: int = Field(default=0, ge=0)

class DocumentStatusUpdate(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "PROCESSING"})
    processed_at: Optional[datetime] = None

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_name: str
    mime_type: str
    file_size_bytes: int
    doc_type: str
    status: str
    storage_key: Optional[str] = None
    created_by: Optional[UUID] = None
    metadata_json: Optional[Dict[str, Any]] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None

class DocumentPaginatedList(BaseModel):
    total: int
    page: int
    limit: int
    data: List[DocumentResponse]
