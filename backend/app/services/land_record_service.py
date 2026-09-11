import uuid
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.core.logging import logger
from app.core.exceptions import RecordNotFoundError, InvalidStateTransitionError, ForbiddenError
from app.models.land_record import LandRecordModel
from app.schemas.record import LandRecordCreate, LandRecordUpdate

class LandRecordService:
    """
    Service managing land record entity persistence, updates, and lifecycle transitions.
    """

    ALLOWED_RECORD_TRANSITIONS = {
        "EXTRACTED": {"NORMALIZED", "VALIDATED", "FLAGGED", "REJECTED"},
        "NORMALIZED": {"VALIDATED", "FLAGGED", "REJECTED"},
        "VALIDATED": {"FLAGGED", "REJECTED", "NORMALIZED"},
        "FLAGGED": {"VALIDATED", "REJECTED", "NORMALIZED"},
        "REJECTED": {"NORMALIZED", "FLAGGED"}
    }

    def check_record_access(self, record: LandRecordModel, user: Optional[Any] = None) -> None:
        """
        Enforces resource-level ownership and RBAC.
        Admins, Reviewers, and Viewers have access to all records.
        Operators can access records they created/uploaded, or unassigned records.
        """
        if not user:
            return
        user_role = getattr(user, "role", None)
        user_id = getattr(user, "id", None)
        role_str = str(user_role).upper()

        if role_str == "OPERATOR":
            if record.created_by is not None and record.created_by != user_id:
                raise ForbiddenError("You do not have permission to access or export this land record.")
            if getattr(record, "document", None) and record.document.created_by is not None:
                if record.document.created_by != user_id:
                    raise ForbiddenError("You do not have permission to access or export this land record.")

    async def create_record(
        self,
        session: AsyncSession,
        payload: LandRecordCreate
    ) -> LandRecordModel:
        """Creates and stores a new land record entity."""
        record = LandRecordModel(
            id=uuid.uuid4(),
            document_id=payload.document_id,
            created_by=payload.created_by,
            state=payload.state,
            district=payload.district,
            tehsil=payload.tehsil,
            village=payload.village,
            khasra_number=payload.khasra_number,
            khata_number=payload.khata_number,
            area_in_hectares=payload.area_in_hectares,
            land_classification=payload.land_classification or "Agricultural",
            owner_name=payload.owner_name,
            co_owners=payload.co_owners,
            patta_number=payload.patta_number,
            registration_number=payload.registration_number,
            mutation_number=payload.mutation_number,
            document_date=payload.document_date,
            confidence_score=payload.confidence_score if payload.confidence_score is not None else 1.0,
            status=payload.status or "EXTRACTED",
            review_status=payload.review_status or "PENDING_REVIEW",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(record)
        await session.flush()
        logger.info(f"Created land record {record.id} (Khasra: {record.khasra_number}, Village: {record.village})")
        return record

    async def get_record(
        self,
        session: AsyncSession,
        record_id: uuid.UUID
    ) -> LandRecordModel:
        """Fetches single land record or raises RecordNotFoundError."""
        result = await session.execute(
            select(LandRecordModel).where(LandRecordModel.id == record_id)
        )
        record = result.scalars().first()
        if not record:
            raise RecordNotFoundError(record_id)
        return record

    async def update_record(
        self,
        session: AsyncSession,
        record_id: uuid.UUID,
        payload: LandRecordUpdate
    ) -> LandRecordModel:
        """Updates specific fields on an existing land record."""
        record = await self.get_record(session, record_id)
        update_dict = payload.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            if field == "status" and value != record.status:
                current = record.status.upper()
                target = value.upper()
                allowed = self.ALLOWED_RECORD_TRANSITIONS.get(current, set())
                if target not in allowed:
                    raise InvalidStateTransitionError(current, target, entity_name="LandRecord")
                record.status = target
            else:
                setattr(record, field, value)

        record.updated_at = datetime.utcnow()
        await session.flush()
        logger.info(f"Updated land record {record.id}")
        return record

    async def list_by_document(
        self,
        session: AsyncSession,
        document_id: uuid.UUID
    ) -> List[LandRecordModel]:
        """Lists all land records extracted from a specific document."""
        result = await session.execute(
            select(LandRecordModel)
            .where(LandRecordModel.document_id == document_id)
            .order_by(LandRecordModel.khasra_number)
        )
        return list(result.scalars().all())

# Global default instance
land_record_service = LandRecordService()
