from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from app.schemas.document import DocumentResponse
from app.schemas.extraction import ExtractionResultResponse
from app.schemas.record import LandRecordResponse
from app.schemas.validation import ValidationCheckResponse
from app.schemas.discrepancy import ComparisonSummaryResponse

class DigitizationPipelineResult(BaseModel):
    document: DocumentResponse
    extraction: ExtractionResultResponse
    records: List[LandRecordResponse]
    validations: List[ValidationCheckResponse]
    discrepancies: Optional[ComparisonSummaryResponse] = None
    summary: str
