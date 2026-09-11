import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.core.logging import logger
from app.models.audit_log import AuditLogModel

class AuditService:
    """
    Append-only persistent audit trail service for security and domain events.
    Does not provide modification or deletion operations.
    """

    async def log_event(
        self,
        session: AsyncSession,
        action: str,
        entity_type: str,
        actor_user_id: Optional[uuid.UUID] = None,
        entity_id: Optional[uuid.UUID] = None,
        previous_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLogModel:
        """
        Appends an immutable audit event to the audit_logs table.
        Sensitive keys (password, token, secret) are stripped defensively.
        """
        def sanitize(d: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
            if not d:
                return None
            sensitive_keys = {"password", "token", "access_token", "secret", "hashed_password"}
            return {k: ("***" if k.lower() in sensitive_keys else v) for k, v in d.items()}

        log_entry = AuditLogModel(
            id=uuid.uuid4(),
            actor_user_id=actor_user_id,
            action=action.upper(),
            entity_type=entity_type.upper(),
            entity_id=entity_id,
            previous_state=sanitize(previous_state),
            new_state=sanitize(new_state),
            metadata_json=sanitize(metadata),
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.utcnow()
        )
        session.add(log_entry)
        await session.flush()
        logger.info(f"Audit event logged: {action} on {entity_type}:{entity_id} by {actor_user_id}")
        return log_entry

    async def list_logs(
        self,
        session: AsyncSession,
        actor_user_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
        page: int = 1,
        limit: int = 50
    ) -> Tuple[int, List[AuditLogModel]]:
        """
        Retrieves paginated audit logs with optional filters.
        """
        query = select(AuditLogModel)

        if actor_user_id:
            query = query.where(AuditLogModel.actor_user_id == actor_user_id)
        if action:
            query = query.where(AuditLogModel.action == action.upper())
        if entity_type:
            query = query.where(AuditLogModel.entity_type == entity_type.upper())
        if entity_id:
            query = query.where(AuditLogModel.entity_id == entity_id)

        count_query = select(func.count(AuditLogModel.id))
        if actor_user_id:
            count_query = count_query.where(AuditLogModel.actor_user_id == actor_user_id)
        if action:
            count_query = count_query.where(AuditLogModel.action == action.upper())
        if entity_type:
            count_query = count_query.where(AuditLogModel.entity_type == entity_type.upper())
        if entity_id:
            count_query = count_query.where(AuditLogModel.entity_id == entity_id)

        total_res = await session.execute(count_query)
        total = total_res.scalar_one()

        offset = (page - 1) * limit
        res = await session.execute(
            query.order_by(desc(AuditLogModel.created_at)).offset(offset).limit(limit)
        )
        items = list(res.scalars().all())
        return total, items

audit_service = AuditService()
