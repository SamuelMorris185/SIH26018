import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.user import UserModel
from app.schemas.user import UserRole
from app.schemas.gis import (
    CadastralMapResponse,
    CadastralMapRecord,
    ParcelLocationBase,
    ParcelLocationResponse,
    GeometryValidationRequest,
    GeometryValidationResponse,
)
from app.services.gis_service import gis_service
from app.api.dependencies.auth import get_current_user, require_role

router = APIRouter(prefix="/map", tags=["Cadastral GIS Map"])

@router.get("/parcels", response_model=CadastralMapResponse)
async def list_cadastral_parcels(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (VALIDATED, FLAGGED, PENDING_REVIEW, etc.)"),
    district: Optional[str] = Query(None, description="Filter by district name"),
    village: Optional[str] = Query(None, description="Filter by village name"),
    has_discrepancies: Optional[bool] = Query(None, description="Filter records with or without discrepancies"),
    limit: int = Query(300, ge=1, le=1000, description="Max parcel features to return"),
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Retrieves spatial cadastral parcel features for interactive map display.
    Applies data minimization to omit sensitive citizen info and enforces RBAC isolation.
    """
    parcels = await gis_service.list_cadastral_parcels(
        session=session,
        current_user=current_user,
        status_filter=status_filter,
        district_filter=district,
        village_filter=village,
        has_discrepancies=has_discrepancies,
        limit=limit
    )
    return CadastralMapResponse(
        total_parcels=len(parcels),
        parcels=parcels
    )

@router.get("/parcels/{record_id}", response_model=CadastralMapRecord)
async def get_parcel_detail(
    record_id: uuid.UUID,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Retrieves spatial details and record summary for a clicked parcel or pin marker.
    """
    return await gis_service.get_parcel_detail(session, record_id, current_user)

@router.post("/geometry/validate", response_model=GeometryValidationResponse)
async def validate_geometry(
    payload: GeometryValidationRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Validates coordinate ranges, GeoJSON topology, vertex limits, and syntax integrity.
    """
    return gis_service.validate_geometry_payload(
        lat=payload.latitude,
        lon=payload.longitude,
        geojson=payload.boundary_geojson,
        coordinate_reference_system=payload.coordinate_reference_system,
    )

@router.post("/parcels/{record_id}", response_model=ParcelLocationResponse, status_code=status.HTTP_200_OK)
async def attach_parcel_location(
    record_id: uuid.UUID,
    payload: ParcelLocationBase,
    current_user: UserModel = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Attaches or updates spatial coordinates and GeoJSON boundary for a land record.
    Requires ADMIN or OPERATOR role and resource ownership.
    """
    loc = await gis_service.attach_parcel_location(
        session=session,
        record_id=record_id,
        location_data=payload,
        current_user=current_user
    )
    await session.commit()
    return ParcelLocationResponse.model_validate(loc)
