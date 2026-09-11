import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import (
    RecordNotFoundError,
    InvalidStateTransitionError,
    DomainException,
    ForbiddenError
)
from app.models.land_record import LandRecordModel
from app.models.user import UserModel
from app.schemas.review import ReviewStatus, ReviewDetailResponse
from app.schemas.user import UserRole
from app.services.audit_service import audit_service

class ReviewService:
    """
    Coordinates human review, approval, rejection, and review audit logging.
    Enforces distinct review states separate from automated machine validation.
    """

    ALLOWED_REVIEW_TRANSITIONS = {
        "NOT_REQUIRED": {"PENDING_REVIEW"},
        "PENDING_REVIEW": {"IN_REVIEW", "APPROVED", "REJECTED", "CHANGES_REQUESTED"},
        "IN_REVIEW": {"APPROVED", "REJECTED", "CHANGES_REQUESTED", "PENDING_REVIEW"},
        "CHANGES_REQUESTED": {"PENDING_REVIEW", "IN_REVIEW", "REJECTED"},
        "APPROVED": {"CHANGES_REQUESTED"}, # Admin-only override
        "REJECTED": {"CHANGES_REQUESTED"}, # Admin-only override
    }

    async def get_record(self, session: AsyncSession, record_id: uuid.UUID) -> LandRecordModel:
        result = await session.execute(
            select(LandRecordModel).where(LandRecordModel.id == record_id)
        )
        record = result.scalars().first()
        if not record:
            raise RecordNotFoundError(record_id)
        return record

    async def get_review_status(self, session: AsyncSession, record_id: uuid.UUID) -> ReviewDetailResponse:
        record = await self.get_record(session, record_id)
        return ReviewDetailResponse(
            record_id=record.id,
            review_status=ReviewStatus(record.review_status or "PENDING_REVIEW"),
            reviewed_by=record.reviewed_by,
            reviewed_at=record.reviewed_at,
            review_notes=record.review_notes,
            rejection_reason=record.rejection_reason,
            land_record_status=record.status,
            updated_at=record.updated_at
        )

    def _validate_transition(self, current: str, target: str, actor: UserModel) -> None:
        if target == current:
            return

        allowed = self.ALLOWED_REVIEW_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise InvalidStateTransitionError(current, target, entity_name="LandRecordReview")

        # Admin override check for terminal states
        if current in {"APPROVED", "REJECTED"} and actor.role != UserRole.ADMIN.value:
            raise ForbiddenError(f"Only ADMIN users can reopen records from '{current}' state.")

    async def submit_for_review(
        self,
        session: AsyncSession,
        record_id: uuid.UUID,
        actor: UserModel,
        notes: Optional[str] = None
    ) -> ReviewDetailResponse:
        """
        Transitions a record to IN_REVIEW.
        """
        record = await self.get_record(session, record_id)
        current = (record.review_status or "PENDING_REVIEW").upper()
        target = "IN_REVIEW"

        self._validate_transition(current, target, actor)

        prev_state = {"review_status": current, "notes": record.review_notes}
        record.review_status = target
        if notes:
            record.review_notes = notes
        record.reviewed_by = actor.id
        record.reviewed_at = datetime.utcnow()
        record.updated_at = datetime.utcnow()

        await session.flush()

        await audit_service.log_event(
            session=session,
            action="RECORD_SUBMITTED_FOR_REVIEW",
            entity_type="LAND_RECORD",
            actor_user_id=actor.id,
            entity_id=record.id,
            previous_state=prev_state,
            new_state={"review_status": target, "notes": record.review_notes}
        )

        return await self.get_review_status(session, record.id)

    async def approve_record(
        self,
        session: AsyncSession,
        record_id: uuid.UUID,
        actor: UserModel,
        notes: Optional[str] = None
    ) -> ReviewDetailResponse:
        """
        Approves a land record. Only REVIEWER or ADMIN role permitted.
        """
        if actor.role not in {UserRole.REVIEWER.value, UserRole.ADMIN.value}:
            raise ForbiddenError("Only REVIEWER or ADMIN users can approve land records.")

        record = await self.get_record(session, record_id)
        current = (record.review_status or "PENDING_REVIEW").upper()
        target = "APPROVED"

        self._validate_transition(current, target, actor)

        prev_state = {"review_status": current}
        record.review_status = target
        if notes:
            record.review_notes = notes
        record.reviewed_by = actor.id
        record.reviewed_at = datetime.utcnow()
        record.rejection_reason = None
        record.updated_at = datetime.utcnow()

        await session.flush()

        await audit_service.log_event(
            session=session,
            action="RECORD_APPROVED",
            entity_type="LAND_RECORD",
            actor_user_id=actor.id,
            entity_id=record.id,
            previous_state=prev_state,
            new_state={"review_status": target, "notes": record.review_notes}
        )

        return await self.get_review_status(session, record.id)

    async def reject_record(
        self,
        session: AsyncSession,
        record_id: uuid.UUID,
        actor: UserModel,
        rejection_reason: str,
        notes: Optional[str] = None
    ) -> ReviewDetailResponse:
        """
        Rejects a land record with mandatory explanation. Only REVIEWER or ADMIN permitted.
        """
        if actor.role not in {UserRole.REVIEWER.value, UserRole.ADMIN.value}:
            raise ForbiddenError("Only REVIEWER or ADMIN users can reject land records.")

        clean_reason = (rejection_reason or "").strip()
        if len(clean_reason) < 5:
            raise DomainException(
                message="A meaningful rejection reason (minimum 5 characters) is mandatory.",
                status_code=422
            )

        record = await self.get_record(session, record_id)
        current = (record.review_status or "PENDING_REVIEW").upper()
        target = "REJECTED"

        self._validate_transition(current, target, actor)

        prev_state = {"review_status": current}
        record.review_status = target
        record.rejection_reason = clean_reason
        if notes:
            record.review_notes = notes
        record.reviewed_by = actor.id
        record.reviewed_at = datetime.utcnow()
        record.updated_at = datetime.utcnow()

        await session.flush()

        await audit_service.log_event(
            session=session,
            action="RECORD_REJECTED",
            entity_type="LAND_RECORD",
            actor_user_id=actor.id,
            entity_id=record.id,
            previous_state=prev_state,
            new_state={
                "review_status": target,
                "rejection_reason": clean_reason,
                "notes": record.review_notes
            }
        )

        return await self.get_review_status(session, record.id)

review_service = ReviewService()
