import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from app.core.config import settings
from app.core.exceptions import AuthenticationError

def get_password_hash(password: str) -> str:
    """
    Hashes a plaintext password using bcrypt with a salt.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plaintext password against a stored bcrypt hash.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Generates a cryptographically signed HMAC-SHA256 JWT access token.
    Claims include sub (subject/user_id), role, iat, and exp.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp())
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt

def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decodes and validates a JWT access token.
    Raises AuthenticationError on expired, malformed, or invalid tokens.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "iat", "exp"]},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Access token has expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid or malformed access token.")
