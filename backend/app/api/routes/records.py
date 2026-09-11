import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db_session
from app.models.user import UserModel
from app.models.extraction import ExtractionResultModel
from app.schemas.user import UserRole
from app.services.land_record_service import land_record_service
from app.services.search_service import search_service
from app.services.validation_service import validation_service
from app.services.comparison_service import comparison_service
from app.services.audit_service import audit_service
from app.services.report_service import verification_report_service
from app.schemas.record import (
    LandRecordResponse,
    LandRecordDetailResponse,
    LandRecordPaginatedList,
    LandRecordCreate,
    LandRecordUpdate,
)
from app.schemas.validation import ValidationCheckResponse
from app.schemas.extraction import ExtractionResultResponse
from app.schemas.discrepancy import DiscrepancyResponse
from app.api.dependencies.auth import get_current_user, require_role

router = APIRouter(prefix="/records", tags=["Land Records"])

@router.get("", response_model=LandRecordPaginatedList)
async def list_land_records(
    state: Optional[str] = Query(None, description="Filter by state"),
    district: Optional[str] = Query(None, description="Filter by district"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (EXTRACTED, NORMALIZED, VALIDATED, FLAGGED, REJECTED)"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve paginated land records with optional geographic and status filters.
    """
    return await search_service.search_records(
        session=session,
        state=state,
        district=district,
        status=status_filter,
        page=page,
        limit=limit
    )

@router.get("/{record_id}", response_model=LandRecordDetailResponse)
async def get_land_record(
    record_id: uuid.UUID,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Fetch a single land record by ID with its latest validation check report and detected discrepancies.
    """
    record = await land_record_service.get_record(session, record_id)
    validations = await validation_service.get_validation_history(record_id, session)
    discrepancies = await comparison_service.get_record_discrepancies(session, record_id)

    latest_val = None
    if validations:
        v = validations[0]
        latest_val = ValidationCheckResponse(
            record_id=v.record_id,
            is_valid=v.is_valid,
            status=v.status,
            rule_results=v.rule_results,
            discrepancy_summary=v.discrepancy_summary,
            validated_at=v.validated_at
        )

    record_dto = LandRecordResponse.model_validate(record)
    response = LandRecordDetailResponse(
        **record_dto.model_dump(),
        latest_validation=latest_val,
        discrepancies=[DiscrepancyResponse.model_validate(d) for d in discrepancies]
    )
    return response

@router.get("/{record_id}/extraction", response_model=ExtractionResultResponse)
async def get_record_extraction(
    record_id: uuid.UUID,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve structured OCR extraction results and field-level evidence for a land record.
    """
    record = await land_record_service.get_record(session, record_id)
    if not record.document_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Land record '{record_id}' is not linked to any source document."
        )

    stmt = (
        select(ExtractionResultModel)
        .where(ExtractionResultModel.document_id == record.document_id)
        .order_by(ExtractionResultModel.extracted_at.desc())
    )
    result = await session.execute(stmt)
    extraction = result.scalars().first()
    if not extraction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No extraction results found for document '{record.document_id}'."
        )

    return ExtractionResultResponse.model_validate(extraction)

@router.post("", response_model=LandRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_land_record(
    payload: LandRecordCreate,
    current_user: UserModel = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Manually create a new land record entry. Requires ADMIN or OPERATOR role.
    """
    if payload.created_by is None:
        payload.created_by = current_user.id
    record = await land_record_service.create_record(session, payload)
    
    await audit_service.log_event(
        session=session,
        action="RECORD_CREATED",
        entity_type="LAND_RECORD",
        actor_user_id=current_user.id,
        entity_id=record.id,
        new_state={"khasra": record.khasra_number, "village": record.village}
    )
    await session.commit()
    return LandRecordResponse.model_validate(record)

@router.patch("/{record_id}", response_model=LandRecordResponse)
async def update_land_record(
    record_id: uuid.UUID,
    payload: LandRecordUpdate,
    current_user: UserModel = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Update land record fields or modify validation status.
    """
    record = await land_record_service.update_record(session, record_id, payload)
    
    await audit_service.log_event(
        session=session,
        action="RECORD_UPDATED",
        entity_type="LAND_RECORD",
        actor_user_id=current_user.id,
        entity_id=record.id,
        new_state={"status": record.status}
    )
    await session.commit()
    return LandRecordResponse.model_validate(record)

@router.get("/{record_id}/validation", response_model=ValidationCheckResponse)
async def get_latest_record_validation(
    record_id: uuid.UUID,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve the latest validation result report for a specific land record.
    """
    await land_record_service.get_record(session, record_id)
    history = await validation_service.get_validation_history(record_id, session)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No validation audits found for land record '{record_id}'."
        )
    v = history[0]
    return ValidationCheckResponse(
        record_id=v.record_id,
        is_valid=v.is_valid,
        status=v.status,
        rule_results=v.rule_results,
        discrepancy_summary=v.discrepancy_summary,
        validated_at=v.validated_at
    )

@router.post("/{record_id}/validate", response_model=ValidationCheckResponse)
async def trigger_record_validation(
    record_id: uuid.UUID,
    current_user: UserModel = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Triggers manual re-validation of an existing land record and persists the audit.
    """
    record = await land_record_service.get_record(session, record_id)
    record_dict = {
        "state": record.state,
        "district": record.district,
        "tehsil": record.tehsil,
        "village": record.village,
        "khasra_number": record.khasra_number,
        "khata_number": record.khata_number,
        "area_in_hectares": float(record.area_in_hectares),
        "land_classification": record.land_classification,
        "confidence_score": record.confidence_score
    }
    result = await validation_service.validate_and_persist(record_id, record_dict, session)
    
    val_action = "RECORD_VALIDATED" if result.is_valid else "RECORD_FLAGGED"
    await audit_service.log_event(
        session=session,
        action=val_action,
        entity_type="LAND_RECORD",
        actor_user_id=current_user.id,
        entity_id=record.id,
        new_state={"is_valid": result.is_valid, "status": result.status}
    )
    await session.commit()
    return result

@router.get("/{record_id}/validations", response_model=List[ValidationCheckResponse])
async def get_record_validations(
    record_id: uuid.UUID,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve complete historical validation audit trail for a specific land record.
    """
    await land_record_service.get_record(session, record_id)
    history = await validation_service.get_validation_history(record_id, session)
    return [
        ValidationCheckResponse(
            record_id=h.record_id,
            is_valid=h.is_valid,
            status=h.status,
            rule_results=h.rule_results,
            discrepancy_summary=h.discrepancy_summary,
            validated_at=h.validated_at
        )
        for h in history
    ]

@router.get("/{record_id}/verification-report")
async def get_verification_report(
    record_id: uuid.UUID,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Generates a secure, point-in-time PDF Verification Report for a land record.
    Includes registry attributes, OCR extraction confidence, rule validation audits,
    cross-record discrepancy analysis, human review decisions, and audit trail references.
    Enforces RBAC and ownership isolation.
    """
    pdf_bytes, filename = await verification_report_service.generate_verification_pdf(
        session=session,
        record_id=record_id,
        current_user=current_user
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )
