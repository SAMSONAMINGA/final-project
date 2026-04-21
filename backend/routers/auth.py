"""
Authentication endpoints.
POST /auth/token - login, return JWT pair
POST /auth/refresh - refresh access token
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from core.security import (
    verify_password, hash_password, create_token_pair,
    verify_token, get_current_user, TokenPayload
)
from models.orm import User
from schemas.api import LoginRequest, TokenResponse, CreateUserRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """
    Login endpoint.
    Accept username & password, return JWT pair (access + refresh tokens).
    
    Access token: 60-min validity
    Refresh token: 7-day validity
    """
    # Find user by username
    result = await db.execute(
        select(User).where(User.username == request.username)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account disabled",
        )
    
    # Create token pair
    return create_token_pair(user.id, user.role.value)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    old_token: str,
) -> TokenResponse:
    """
    Refresh access token using refresh token.
    """
    # Verify refresh token
    payload = verify_token(old_token, token_type="refresh")
    
    # Issue new token pair
    return create_token_pair(payload.sub, payload.role)


@router.post("/users", response_model=UserResponse)
async def create_user(
    request: CreateUserRequest,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> UserResponse:
    """
    Create new user (admin only).
    """
    # Check admin privilege
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    # Check username doesn't exist
    existing = await db.execute(
        select(User).where(User.username == request.username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )
    
    # Create user
    user = User(
        username=request.username,
        email=request.email,
        hashed_password=hash_password(request.password),
        role=request.role,
        is_active=True,
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
