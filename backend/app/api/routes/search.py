import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.user import UserModel
from app.services.search_service import search_service
from app.schemas.record import LandRecordPaginatedList
from app.api.dependencies.auth import get_current_user

router = APIRouter(prefix="/search", tags=["Search"])

@router.get("", response_model=LandRecordPaginatedList)
async def search_land_records(
    state: Optional[str] = Query(None, description="Filter by state (case-insensitive)"),
    district: Optional[str] = Query(None, description="Filter by district (case-insensitive)"),
    tehsil: Optional[str] = Query(None, description="Filter by tehsil (case-insensitive)"),
    village: Optional[str] = Query(None, description="Filter by village (case-insensitive)"),
    khasra_number: Optional[str] = Query(None, description="Partial or exact match on khasra parcel number"),
    khata_number: Optional[str] = Query(None, description="Exact match on khata account number"),
    status: Optional[str] = Query(None, description="Filter by record status (EXTRACTED, NORMALIZED, VALIDATED, FLAGGED, REJECTED)"),
    document_id: Optional[uuid.UUID] = Query(None, description="Filter by source document UUID"),
    min_area: Optional[float] = Query(None, ge=0, description="Minimum parcel area in hectares"),
    max_area: Optional[float] = Query(None, ge=0, description="Maximum parcel area in hectares"),
    sort_by: str = Query("created_at", description="Field to sort by (created_at, updated_at, area_in_hectares, khasra_number, village, status)"),
    sort_order: str = Query("desc", description="Sort direction ('asc' or 'desc')"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Advanced multi-criteria search endpoint executing directly against database.
    Supports complex filtering, pagination, and sorting for authenticated users.
    """
    return await search_service.search_records(
        session=session,
        current_user=current_user,
        state=state,
        district=district,
        tehsil=tehsil,
        village=village,
        khasra_number=khasra_number,
        khata_number=khata_number,
        status=status,
        document_id=document_id,
        min_area=min_area,
        max_area=max_area,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        limit=limit
    )
