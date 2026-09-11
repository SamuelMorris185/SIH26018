import uuid
import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateTransitionError, DiscrepancyNotFoundError
from app.models.discrepancy import DiscrepancyModel
from app.schemas.discrepancy import DiscrepancyUpdate, DiscrepancyStatus
from app.services.comparison_service import comparison_service

@pytest.mark.asyncio
async def test_valid_discrepancy_lifecycle_transitions(db_session: AsyncSession):
    # Setup test discrepancy in OPEN state
    disc = DiscrepancyModel(
        id=uuid.uuid4(),
        record_id=uuid.uuid4(),
        discrepancy_type="OWNER_MISMATCH",
        severity="CRITICAL",
        description="Owner mismatch on parcel 104/2",
        status=DiscrepancyStatus.OPEN.value,
        confidence=0.95,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(disc)
    await db_session.flush()

    # Transition 1: OPEN -> ACKNOWLEDGED (Valid)
    upd = DiscrepancyUpdate(status=DiscrepancyStatus.ACKNOWLEDGED, resolution_notes="Investigating mismatch")
    updated = await comparison_service.update_discrepancy_status(db_session, disc.id, upd)
    assert updated.status == "ACKNOWLEDGED"

    # Transition 2: ACKNOWLEDGED -> RESOLVED (Valid)
    upd = DiscrepancyUpdate(status=DiscrepancyStatus.RESOLVED, resolution_notes="Verified title deed")
    updated = await comparison_service.update_discrepancy_status(db_session, disc.id, upd)
    assert updated.status == "RESOLVED"

    # Transition 3: RESOLVED -> OPEN (Valid re-opening)
    upd = DiscrepancyUpdate(status=DiscrepancyStatus.OPEN, resolution_notes="New conflicting claim emerged")
    updated = await comparison_service.update_discrepancy_status(db_session, disc.id, upd)
    assert updated.status == "OPEN"

    # Transition 4: OPEN -> DISMISSED (Valid)
    upd = DiscrepancyUpdate(status=DiscrepancyStatus.DISMISSED, resolution_notes="Minor typo ignored")
    updated = await comparison_service.update_discrepancy_status(db_session, disc.id, upd)
    assert updated.status == "DISMISSED"

@pytest.mark.asyncio
async def test_invalid_discrepancy_transitions_raise_conflict(db_session: AsyncSession):
    # Discrepancy in RESOLVED state
    disc = DiscrepancyModel(
        id=uuid.uuid4(),
        record_id=uuid.uuid4(),
        discrepancy_type="AREA_MISMATCH",
        severity="HIGH",
        description="Area divergence detected",
        status=DiscrepancyStatus.RESOLVED.value,
        confidence=0.90,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(disc)
    await db_session.flush()

    # Attempt illegal transition: RESOLVED -> ACKNOWLEDGED (Must fail with InvalidStateTransitionError)
    upd = DiscrepancyUpdate(status=DiscrepancyStatus.ACKNOWLEDGED)
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        await comparison_service.update_discrepancy_status(db_session, disc.id, upd)

    assert exc_info.value.status_code == 409
    assert "cannot transition from 'RESOLVED' to 'ACKNOWLEDGED'" in exc_info.value.message

@pytest.mark.asyncio
async def test_dismissed_cannot_transition_directly_to_resolved(db_session: AsyncSession):
    # Discrepancy in DISMISSED state
    disc = DiscrepancyModel(
        id=uuid.uuid4(),
        record_id=uuid.uuid4(),
        discrepancy_type="SURVEY_CONFLICT",
        severity="MEDIUM",
        description="Classification conflict",
        status=DiscrepancyStatus.DISMISSED.value,
        confidence=0.85,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(disc)
    await db_session.flush()

    # Attempt illegal transition: DISMISSED -> RESOLVED (Must fail with 409)
    upd = DiscrepancyUpdate(status=DiscrepancyStatus.RESOLVED)
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        await comparison_service.update_discrepancy_status(db_session, disc.id, upd)

    assert exc_info.value.status_code == 409
