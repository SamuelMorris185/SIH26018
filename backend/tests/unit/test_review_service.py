import uuid
import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.land_record import LandRecordModel
from app.models.user import UserModel
from app.schemas.review import ReviewStatus
from app.core.exceptions import (
    ForbiddenError,
    InvalidStateTransitionError,
    DomainException,
    RecordNotFoundError
)
from app.services.review_service import ReviewService

@pytest.mark.anyio
async def test_review_service_lifecycle_and_transitions(db_session: AsyncSession):
    service = ReviewService()

    # Create dummy users
    operator = UserModel(
        id=uuid.uuid4(),
        email="operator1@gov.in",
        hashed_password="hash",
        full_name="Operator One",
        role="OPERATOR",
        is_active=True,
        created_at=datetime.utcnow()
    )
    reviewer = UserModel(
        id=uuid.uuid4(),
        email="reviewer1@gov.in",
        hashed_password="hash",
        full_name="Reviewer One",
        role="REVIEWER",
        is_active=True,
        created_at=datetime.utcnow()
    )
    admin = UserModel(
        id=uuid.uuid4(),
        email="admin1@gov.in",
        hashed_password="hash",
        full_name="Admin One",
        role="ADMIN",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add_all([operator, reviewer, admin])
    await db_session.flush()

    # Create sample record in PENDING_REVIEW
    record = LandRecordModel(
        id=uuid.uuid4(),
        state="Madhya Pradesh",
        district="Bhopal",
        tehsil="Huzur",
        village="Kolar",
        khasra_number="205",
        khata_number="12",
        area_in_hectares=2.5,
        land_classification="Agricultural",
        confidence_score=0.92,
        status="FLAGGED",
        review_status="PENDING_REVIEW",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(record)
    await db_session.flush()

    # 1. Operator attempts to approve directly -> Forbidden
    with pytest.raises(ForbiddenError):
        await service.approve_record(db_session, record.id, actor=operator)

    # 2. Operator submits record for review -> Transitions to IN_REVIEW
    in_review = await service.submit_for_review(
        db_session, record.id, actor=operator, notes="Flagged area boundary requires inspection"
    )
    assert in_review.review_status == ReviewStatus.IN_REVIEW
    assert in_review.reviewed_by == operator.id

    # 3. Reviewer rejects without adequate explanation (< 5 chars) -> Fails
    with pytest.raises(DomainException) as exc_info:
        await service.reject_record(
            db_session, record.id, actor=reviewer, rejection_reason="bad"
        )
    assert exc_info.value.status_code == 422

    # 4. Reviewer rejects with proper explanation -> Transitions to REJECTED
    rejected = await service.reject_record(
        db_session,
        record.id,
        actor=reviewer,
        rejection_reason="Boundary overlap detected with parcel 206 based on manual survey sheet."
    )
    assert rejected.review_status == ReviewStatus.REJECTED
    assert "Boundary overlap" in rejected.rejection_reason

    # 5. Reviewer attempts to reopen REJECTED directly to IN_REVIEW -> InvalidStateTransitionError
    with pytest.raises(InvalidStateTransitionError):
        await service.submit_for_review(db_session, record.id, actor=reviewer)

    # 6. Non-admin attempts to reopen to CHANGES_REQUESTED -> ForbiddenError (only Admin can reopen)
    with pytest.raises(ForbiddenError):
        service._validate_transition("REJECTED", "CHANGES_REQUESTED", actor=reviewer)

    # 7. Admin reopens record to CHANGES_REQUESTED -> Succeeds without error
    service._validate_transition("REJECTED", "CHANGES_REQUESTED", actor=admin)

    # 7. Non-existent record check
    with pytest.raises(RecordNotFoundError):
        await service.get_review_status(db_session, uuid.uuid4())
