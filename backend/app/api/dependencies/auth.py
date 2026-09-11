import uuid
from typing import Optional, List
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthenticationError, ForbiddenError
from app.core.security import decode_access_token
from app.db.session import get_db_session
from app.models.user import UserModel
from app.schemas.user import UserRole
from app.services.user_service import user_service

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False
)

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session)
) -> UserModel:
    """
    Authenticates request via JWT Bearer token and returns the active UserModel.
    Raises AuthenticationError (HTTP 401) on missing, invalid, or expired tokens.
    """
    if not token:
        raise AuthenticationError("Authentication required. Please provide a Bearer access token.")

    payload = decode_access_token(token)
    sub = payload.get("sub")
    if not sub:
        raise AuthenticationError("Invalid token subject claim.")

    try:
        user_uuid = uuid.UUID(sub)
    except ValueError:
        raise AuthenticationError("Invalid token user identifier.")

    user = await user_service.get_by_id(session, user_uuid)
    if not user.is_active:
        raise AuthenticationError("User account is deactivated.")

    return user

async def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session)
) -> Optional[UserModel]:
    """
    Optional authentication: returns UserModel if valid token provided, else None.
    """
    if not token:
        return None
    try:
        return await get_current_user(token=token, session=session)
    except AuthenticationError:
        return None

def require_role(*allowed_roles: UserRole):
    """
    Role-Based Access Control (RBAC) dependency factory.
    Returns 403 Forbidden if authenticated user's role is not in allowed_roles.
    """
    allowed_values = {r.value if isinstance(r, UserRole) else str(r) for r in allowed_roles}

    async def role_dependency(current_user: UserModel = Depends(get_current_user)) -> UserModel:
        if current_user.role not in allowed_values:
            raise ForbiddenError(
                f"Access denied: action requires one of {sorted(list(allowed_values))}, "
                f"but your role is '{current_user.role}'."
            )
        return current_user

    return role_dependency
