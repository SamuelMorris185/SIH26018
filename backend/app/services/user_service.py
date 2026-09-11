import uuid
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.core.security import get_password_hash, verify_password
from app.core.exceptions import UserNotFoundError, UserAlreadyExistsError, AuthenticationError
from app.models.user import UserModel
from app.schemas.user import UserCreate, UserUpdate, UserRole

class UserService:
    """
    Manages user registration, authentication, role assignment, and retrieval.
    """

    async def get_by_id(self, session: AsyncSession, user_id: uuid.UUID) -> UserModel:
        result = await session.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalars().first()
        if not user:
            raise UserNotFoundError(user_id)
        return user

    async def get_by_email(self, session: AsyncSession, email: str) -> Optional[UserModel]:
        clean_email = email.lower().strip()
        result = await session.execute(select(UserModel).where(UserModel.email == clean_email))
        return result.scalars().first()

    async def authenticate(self, session: AsyncSession, email: str, password: str) -> UserModel:
        """
        Validates credentials securely.
        Returns user on success; raises AuthenticationError with generic message on failure.
        """
        user = await self.get_by_email(session, email)
        if not user:
            raise AuthenticationError("Invalid email or password.")
        
        if not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password.")

        if not user.is_active:
            raise AuthenticationError("User account is deactivated. Contact an administrator.")

        return user

    async def create_user(self, session: AsyncSession, payload: UserCreate) -> UserModel:
        """
        Creates a new user with hashed password. Enforces email uniqueness.
        """
        clean_email = payload.email.lower().strip()
        existing = await self.get_by_email(session, clean_email)
        if existing:
            raise UserAlreadyExistsError(clean_email)

        user = UserModel(
            id=uuid.uuid4(),
            email=clean_email,
            hashed_password=get_password_hash(payload.password),
            full_name=payload.full_name.strip(),
            role=payload.role.value if isinstance(payload.role, UserRole) else str(payload.role),
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(user)
        await session.flush()
        return user

    async def update_user(self, session: AsyncSession, user_id: uuid.UUID, payload: UserUpdate) -> UserModel:
        user = await self.get_by_id(session, user_id)
        
        if payload.full_name is not None:
            user.full_name = payload.full_name.strip()
        if payload.role is not None:
            user.role = payload.role.value if isinstance(payload.role, UserRole) else str(payload.role)
        if payload.is_active is not None:
            user.is_active = payload.is_active

        user.updated_at = datetime.utcnow()
        await session.flush()
        return user

    async def list_users(self, session: AsyncSession, page: int = 1, limit: int = 20) -> Tuple[int, List[UserModel]]:
        total_res = await session.execute(select(func.count(UserModel.id)))
        total = total_res.scalar_one()

        offset = (page - 1) * limit
        query = select(UserModel).order_by(desc(UserModel.created_at)).offset(offset).limit(limit)
        res = await session.execute(query)
        users = list(res.scalars().all())

        return total, users

user_service = UserService()
