"""
JWT authentication and RBAC (Role-Based Access Control).
Implements HS256 with access token (60 min) + refresh token (7 days).

Design decisions:
- JWT HS256 sufficient for internal Kenya deployment
- Sub claim contains user_id, includes 'role' claim for RBAC
- Refresh tokens stored in DB for revocation capability
- Password hashing via bcrypt (salted, 12 rounds)
- CORS strict allowlist from settings
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
import logging

from core.config import settings

logger = logging.getLogger(__name__)

# Password hashing context (bcrypt, 12 rounds)
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)

# HTTP Bearer scheme for FastAPI
security = HTTPBearer()


class TokenPayload(BaseModel):
    """JWT token payload structure."""
    sub: int  # user_id
    role: str  # "user" or "admin"
    exp: int  # expiration timestamp
    iat: int  # issued at timestamp
    type: str  # "access" or "refresh"


class TokenResponse(BaseModel):
    """Response when issuing tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until expiration


def hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain, hashed)


def hash_device_id(device_id: str) -> str:
    """
    Hash device_id for anonymization (SHA-256).
    Used to store anonymous barometer readings without PII.
    """
    import hashlib
    return hashlib.sha256(device_id.encode()).hexdigest()


def create_access_token(user_id: int, role: str) -> str:
    """
    Create JWT access token (60 min validity).
    
    Args:
        user_id: Database user ID
        role: "user" or "admin" for RBAC
    
    Returns:
        Encoded JWT token
    """
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.access_token_expire_minutes)
    
    payload = {
        "sub": user_id,
        "role": role,
        "exp": int(expires.timestamp()),
        "iat": int(now.timestamp()),
        "type": "access",
    }
    
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(user_id: int, role: str) -> str:
    """
    Create JWT refresh token (7 day validity).
    
    Args:
        user_id: Database user ID
        role: User's role
    
    Returns:
        Encoded JWT token
    """
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=settings.refresh_token_expire_days)
    
    payload = {
        "sub": user_id,
        "role": role,
        "exp": int(expires.timestamp()),
        "iat": int(now.timestamp()),
        "type": "refresh",
    }
    
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def verify_token(token: str, token_type: str = "access") -> TokenPayload:
    """
    Verify JWT token and extract payload.
    
    Args:
        token: Encoded JWT token
        token_type: "access" or "refresh"
    
    Returns:
        Decoded token payload
    
    Raises:
        HTTPException if token invalid/expired
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        
        # Validate token type
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        
        return TokenPayload(**payload)
    
    except JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


async def get_current_user(
    credentials: HTTPAuthCredentials = Depends(security),
) -> TokenPayload:
    """
    Dependency for protected routes.
    Extracts and validates JWT from Authorization header.
    
    Args:
        credentials: Extracted from "Bearer {token}" header
    
    Returns:
        Verified token payload (user_id, role)
    
    Raises:
        HTTPException if token invalid
    """
    return verify_token(credentials.credentials, token_type="access")


async def get_current_admin(
    user: TokenPayload = Depends(get_current_user),
) -> TokenPayload:
    """
    Dependency for admin-only routes.
    Verifies user has "admin" role.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


def create_token_pair(user_id: int, role: str) -> TokenResponse:
    """
    Create both access and refresh tokens.
    
    Returns:
        TokenResponse with both tokens and expiration
    """
    access_token = create_access_token(user_id, role)
    refresh_token = create_refresh_token(user_id, role)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )
