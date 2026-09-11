import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.user import UserModel
from app.schemas.user import UserRole
from app.schemas.audit import AuditLogListResponse, AuditLogResponse
from app.services.audit_service import audit_service
from app.api.dependencies.auth import require_role

router = APIRouter(prefix="/audit-logs", tags=["Auditability & Governance"])

@router.get("", response_model=AuditLogListResponse)
async def get_audit_logs(
    actor_user_id: Optional[uuid.UUID] = Query(None, description="Filter by user who performed action"),
    action: Optional[str] = Query(None, description="Filter by action name (e.g. LOGIN_SUCCESS, RECORD_APPROVED)"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (e.g. USER, DOCUMENT, LAND_RECORD)"),
    entity_id: Optional[uuid.UUID] = Query(None, description="Filter by target entity ID"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_admin: UserModel = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve immutable system audit logs. Accessible exclusively by administrators.
    """
    total, items = await audit_service.list_logs(
        session=session,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        page=page,
        limit=limit
    )

    return AuditLogListResponse(
        total=total,
        page=page,
        limit=limit,
        items=[AuditLogResponse.model_validate(item) for item in items]
    )
