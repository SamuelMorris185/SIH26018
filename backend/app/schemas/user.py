import uuid
from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    REVIEWER = "REVIEWER"
    VIEWER = "VIEWER"

class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=150)
    role: UserRole = UserRole.OPERATOR

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128, description="Plaintext password to be hashed")

    @field_validator("password")
    @classmethod
    def validate_bcrypt_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes for bcrypt")
        return value

class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=150)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
