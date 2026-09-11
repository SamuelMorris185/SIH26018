from datetime import datetime
from typing import List, Optional, Any, Dict
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

class RuleValidationResult(BaseModel):
    rule_name: str
    passed: bool
    message: str
    severity: str = Field(default="ERROR", json_schema_extra={"example": "ERROR"})

class ValidationCheckResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    record_id: UUID
    is_valid: bool
    status: str = Field(..., json_schema_extra={"example": "VALIDATED"})
    rule_results: List[RuleValidationResult]
    discrepancy_summary: Optional[str] = None
    validated_at: Optional[datetime] = None

class ValidationResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    record_id: UUID
    is_valid: bool
    status: str
    rule_results: List[RuleValidationResult]
    discrepancy_summary: Optional[str] = None
    validated_at: datetime
