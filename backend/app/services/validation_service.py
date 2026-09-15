import uuid
from datetime import timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.logging import logger
from app.schemas.validation import ValidationCheckResponse
from app.services.validation.engine import ValidationEngine
from app.models.validation import ValidationResultModel
from app.models.land_record import LandRecordModel
from app.core.exceptions import RecordNotFoundError

class ValidationService:
    """
    Validation service coordinating record verification checks and audit persistence.
    """

    def __init__(self, engine: Optional[ValidationEngine] = None):
        self.engine = engine or ValidationEngine()

    @staticmethod
    async def validate_land_record(record_id: uuid.UUID, record_data: Dict[str, Any]) -> ValidationCheckResponse:
        """
        Pure validation evaluation without persistence (backward compatible with Phase 1).
        """
        engine = ValidationEngine()
        return engine.evaluate_record(record_id, record_data)

    async def validate_and_persist(
        self,
        record_id: uuid.UUID,
        record_data: Dict[str, Any],
        session: AsyncSession
    ) -> ValidationCheckResponse:
        """
        Runs the validation engine and saves the ValidationResultModel in the database,
        updating the LandRecordModel status to VALIDATED or FLAGGED.
        """
        evaluation = self.engine.evaluate_record(record_id, record_data)

        # Create validation result record
        val_model = ValidationResultModel(
            id=uuid.uuid4(),
            record_id=record_id,
            is_valid=evaluation.is_valid,
            status=evaluation.status,
            rule_results=[r.model_dump() for r in evaluation.rule_results],
            discrepancy_summary=evaluation.discrepancy_summary,
            # Existing schema stores naive UTC, as do all other audit timestamps.
            validated_at=evaluation.validated_at.astimezone(timezone.utc).replace(tzinfo=None)
        )
        session.add(val_model)

        # Update record status in DB
        result = await session.execute(select(LandRecordModel).where(LandRecordModel.id == record_id))
        record = result.scalars().first()
        if record:
            record.status = evaluation.status

        await session.flush()
        return evaluation

    async def get_validation_history(
        self,
        record_id: uuid.UUID,
        session: AsyncSession
    ) -> List[ValidationResultModel]:
        """
        Retrieves all validation audits conducted on a land record.
        """
        result = await session.execute(
            select(ValidationResultModel)
            .where(ValidationResultModel.record_id == record_id)
            .order_by(ValidationResultModel.validated_at.desc())
        )
        return list(result.scalars().all())

# Global default instance
validation_service = ValidationService()
