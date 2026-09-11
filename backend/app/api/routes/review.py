import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.user import UserModel
from app.schemas.user import UserRole
from app.schemas.review import (
    ReviewSubmitRequest,
    ReviewApproveRequest,
    ReviewRejectRequest,
    ReviewDetailResponse
)
from app.services.review_service import review_service
from app.api.dependencies.auth import get_current_user, require_role

router = APIRouter(prefix="/records", tags=["Human Review & Approval"])

@router.get("/{record_id}/review", response_model=ReviewDetailResponse)
async def get_record_review(
    record_id: uuid.UUID,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve human review status, notes, rejection reasons, and reviewer identity.
    """
    return await review_service.get_review_status(session, record_id)

@router.post("/{record_id}/submit-review", response_model=ReviewDetailResponse)
async def submit_record_for_review(
    record_id: uuid.UUID,
    payload: ReviewSubmitRequest,
    current_user: UserModel = Depends(require_role(UserRole.OPERATOR, UserRole.REVIEWER, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Submit or assign a land record for human review (transitions to IN_REVIEW).
    """
    result = await review_service.submit_for_review(
        session=session,
        record_id=record_id,
        actor=current_user,
        notes=payload.notes
    )
    await session.commit()
    return result

@router.post("/{record_id}/approve", response_model=ReviewDetailResponse)
async def approve_record(
    record_id: uuid.UUID,
    payload: ReviewApproveRequest,
    current_reviewer: UserModel = Depends(require_role(UserRole.REVIEWER, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Approve a land record. Permitted exclusively for REVIEWER and ADMIN roles.
    """
    result = await review_service.approve_record(
        session=session,
        record_id=record_id,
        actor=current_reviewer,
        notes=payload.notes
    )
    await session.commit()
    return result

@router.post("/{record_id}/reject", response_model=ReviewDetailResponse)
async def reject_record(
    record_id: uuid.UUID,
    payload: ReviewRejectRequest,
    current_reviewer: UserModel = Depends(require_role(UserRole.REVIEWER, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Reject a land record with mandatory justification. Permitted exclusively for REVIEWER and ADMIN.
    """
    result = await review_service.reject_record(
        session=session,
        record_id=record_id,
        actor=current_reviewer,
        rejection_reason=payload.rejection_reason,
        notes=payload.notes
    )
    await session.commit()
    return result
