import uuid
from typing import List
from fastapi import APIRouter, Depends, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.core.exceptions import AuthenticationError
from app.db.session import get_db_session
from app.models.user import UserModel
from app.schemas.user import (
    LoginRequest,
    TokenResponse,
    UserResponse,
    UserCreate,
    UserUpdate,
    UserRole
)
from app.services.user_service import user_service
from app.services.audit_service import audit_service
from app.api.dependencies.auth import get_current_user, require_role

router = APIRouter(prefix="/auth", tags=["Authentication & Access Control"])

@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Authenticate user with email and password.
    Returns signed JWT access token on success.
    """
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        user = await user_service.authenticate(session, payload.email, payload.password)
    except AuthenticationError as exc:
        await audit_service.log_event(
            session=session,
            action="LOGIN_FAILURE",
            entity_type="USER",
            metadata={"email": payload.email, "reason": exc.message},
            ip_address=client_ip,
            user_agent=user_agent
        )
        await session.commit()
        raise exc

    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    await audit_service.log_event(
        session=session,
        action="LOGIN_SUCCESS",
        entity_type="USER",
        actor_user_id=user.id,
        entity_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent
    )
    await session.commit()

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in_seconds,
        user=UserResponse.model_validate(user)
    )

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserModel = Depends(get_current_user)):
    """
    Retrieve profile of the currently authenticated user.
    """
    return UserResponse.model_validate(current_user)

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_by_admin(
    payload: UserCreate,
    current_admin: UserModel = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Admin-only endpoint to create new system users with assigned roles.
    """
    user = await user_service.create_user(session, payload)
    
    await audit_service.log_event(
        session=session,
        action="USER_CREATED",
        entity_type="USER",
        actor_user_id=current_admin.id,
        entity_id=user.id,
        new_state={"email": user.email, "role": user.role}
    )
    await session.commit()
    return UserResponse.model_validate(user)

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_admin: UserModel = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Admin-only endpoint to list all system users.
    """
    _, users = await user_service.list_users(session, page=page, limit=limit)
    return [UserResponse.model_validate(u) for u in users]

@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user_by_admin(
    user_id: uuid.UUID,
    payload: UserUpdate,
    current_admin: UserModel = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Admin-only endpoint to modify user roles or toggle active status.
    """
    prev_user = await user_service.get_by_id(session, user_id)
    prev_state = {"role": prev_user.role, "is_active": prev_user.is_active}

    updated = await user_service.update_user(session, user_id, payload)

    action = "USER_ROLE_CHANGED" if payload.role and payload.role != prev_state["role"] else (
        "USER_DEACTIVATED" if payload.is_active is False else "USER_UPDATED"
    )
    await audit_service.log_event(
        session=session,
        action=action,
        entity_type="USER",
        actor_user_id=current_admin.id,
        entity_id=updated.id,
        previous_state=prev_state,
        new_state={"role": updated.role, "is_active": updated.is_active}
    )
    await session.commit()
    return UserResponse.model_validate(updated)
