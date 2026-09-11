import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db_session
from app.models.user import UserModel
from app.models.land_record import LandRecordModel
from app.models.discrepancy import DiscrepancyModel
from app.schemas.user import UserRole
from app.core.exceptions import RecordNotFoundError, DiscrepancyNotFoundError, ForbiddenError
from app.schemas.discrepancy import (
    DiscrepancyResponse,
    DiscrepancyUpdate,
    DiscrepancyPaginatedList,
    RecordComparisonResponse,
    ComparisonSummaryResponse,
)
from app.services.comparison_service import comparison_service
from app.api.dependencies.auth import get_current_user, require_role

router = APIRouter(tags=["Cross-Record Discrepancy Detection"])

@router.get("/discrepancies", response_model=DiscrepancyPaginatedList)
async def list_all_discrepancies(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (OPEN, ACKNOWLEDGED, RESOLVED, DISMISSED)"),
    severity: Optional[str] = Query(None, description="Filter by severity (CRITICAL, HIGH, MEDIUM, LOW, INFO)"),
    discrepancy_type: Optional[str] = Query(None, description="Filter by discrepancy type"),
    record_id: Optional[uuid.UUID] = Query(None, description="Filter by land record ID"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve paginated discrepancies with optional status, severity, and type filters.
    """
    query = select(DiscrepancyModel)
    count_query = select(func.count(DiscrepancyModel.id))

    if status_filter:
        query = query.where(DiscrepancyModel.status == status_filter.upper())
        count_query = count_query.where(DiscrepancyModel.status == status_filter.upper())
    if severity:
        query = query.where(DiscrepancyModel.severity == severity.upper())
        count_query = count_query.where(DiscrepancyModel.severity == severity.upper())
    if discrepancy_type:
        query = query.where(DiscrepancyModel.discrepancy_type == discrepancy_type.upper())
        count_query = count_query.where(DiscrepancyModel.discrepancy_type == discrepancy_type.upper())
    if record_id:
        query = query.where(DiscrepancyModel.record_id == record_id)
        count_query = count_query.where(DiscrepancyModel.record_id == record_id)

    total_res = await session.execute(count_query)
    total = total_res.scalar_one() or 0

    offset = (page - 1) * limit
    results = await session.execute(
        query.order_by(DiscrepancyModel.created_at.desc()).offset(offset).limit(limit)
    )
    items = list(results.scalars().all())

    return DiscrepancyPaginatedList(
        total=total,
        page=page,
        limit=limit,
        data=[DiscrepancyResponse.model_validate(d) for d in items]
    )


def _verify_record_access(record: LandRecordModel, user: UserModel) -> None:
    """Ensures operators cannot access or modify records owned by other operators."""
    if user.role in (UserRole.ADMIN.value, UserRole.REVIEWER.value, UserRole.VIEWER.value):
        return
    if user.role == UserRole.OPERATOR.value:
        if record.created_by is not None and record.created_by != user.id:
            raise ForbiddenError("You do not have permission to access records created by another operator.")

@router.get("/records/{record_id}/discrepancies", response_model=List[DiscrepancyResponse])
async def get_record_discrepancies(
    record_id: uuid.UUID,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve all discrepancies detected for a specific land record.
    Enforces resource ownership isolation for operators.
    """
    res = await session.execute(select(LandRecordModel).where(LandRecordModel.id == record_id))
    record = res.scalars().first()
    if not record:
        raise RecordNotFoundError(record_id)
    _verify_record_access(record, current_user)

    discrepancies = await comparison_service.get_record_discrepancies(session, record_id)
    return [DiscrepancyResponse.model_validate(d) for d in discrepancies]

@router.post("/records/{record_id}/compare", response_model=ComparisonSummaryResponse)
async def trigger_record_comparison(
    record_id: uuid.UUID,
    current_user: UserModel = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Manually trigger cross-document comparison and discrepancy detection on a land record.
    Requires ADMIN or OPERATOR role. Enforces operator resource isolation.
    """
    res = await session.execute(select(LandRecordModel).where(LandRecordModel.id == record_id))
    record = res.scalars().first()
    if not record:
        raise RecordNotFoundError(record_id)
    _verify_record_access(record, current_user)

    summary = await comparison_service.compare_record(session, record_id)
    await session.commit()
    return summary

@router.get("/records/{record_id}/comparisons", response_model=List[RecordComparisonResponse])
async def get_record_comparisons(
    record_id: uuid.UUID,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve historical comparison pairings for a land record.
    """
    res = await session.execute(select(LandRecordModel).where(LandRecordModel.id == record_id))
    record = res.scalars().first()
    if not record:
        raise RecordNotFoundError(record_id)
    _verify_record_access(record, current_user)

    comparisons = await comparison_service.get_record_comparisons(session, record_id)
    return [
        RecordComparisonResponse(
            id=c.id,
            record_id=c.record_id,
            compared_record_id=c.compared_record_id,
            match_type=c.match_type,
            discrepancy_count=c.discrepancy_count,
            highest_severity=c.highest_severity,
            status=c.status,
            compared_at=c.compared_at,
            discrepancies=[DiscrepancyResponse.model_validate(d) for d in c.discrepancies]
        )
        for c in comparisons
    ]

@router.patch("/discrepancies/{discrepancy_id}", response_model=DiscrepancyResponse)
async def update_discrepancy_status(
    discrepancy_id: uuid.UUID,
    payload: DiscrepancyUpdate,
    current_user: UserModel = Depends(require_role(UserRole.ADMIN, UserRole.REVIEWER)),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Updates discrepancy resolution status (ACKNOWLEDGED, RESOLVED, DISMISSED).
    Requires REVIEWER or ADMIN role. Generates an append-only audit event.
    """
    discrepancy = await comparison_service.update_discrepancy_status(
        session=session,
        discrepancy_id=discrepancy_id,
        payload=payload,
        actor_user_id=current_user.id
    )
    await session.commit()
    return DiscrepancyResponse.model_validate(discrepancy)
