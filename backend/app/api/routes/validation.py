import uuid
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.user import UserModel
from app.schemas.user import UserRole
from app.services.land_record_service import land_record_service
from app.services.validation_service import validation_service
from app.services.audit_service import audit_service
from app.schemas.validation import ValidationCheckResponse
from app.api.dependencies.auth import get_current_user, require_role

router = APIRouter(prefix="/validation", tags=["Validation Engine"])

@router.post("/records/{record_id}", response_model=ValidationCheckResponse)
async def validate_record(
    record_id: uuid.UUID,
    current_user: UserModel = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Executes the modular rule verification engine on an existing land record and persists the audit result.
    Updates record status to VALIDATED or FLAGGED.
    """
    record = await land_record_service.get_record(session, record_id, current_user)
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

@router.get("/records/{record_id}/history", response_model=List[ValidationCheckResponse])
async def get_record_validation_history(
    record_id: uuid.UUID,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Retrieves historical verification audit trail for the given record.
    """
    await land_record_service.get_record(session, record_id, current_user)
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
