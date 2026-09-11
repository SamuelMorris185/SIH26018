import uuid
from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class ReviewStatus(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING_REVIEW = "PENDING_REVIEW"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"

class ReviewSubmitRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=1000, description="Notes on submission for human review")

class ReviewApproveRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=1000, description="Optional approval comments")

class ReviewRejectRequest(BaseModel):
    rejection_reason: str = Field(..., min_length=5, max_length=1000, description="Detailed reason for rejection (required)")
    notes: Optional[str] = Field(None, max_length=1000, description="Additional review commentary")

class ReviewDetailResponse(BaseModel):
    record_id: uuid.UUID
    review_status: ReviewStatus
    reviewed_by: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    land_record_status: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
