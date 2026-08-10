from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt
import uuid

from database.database import get_db
from models.models import User, ActivityEvent, Document
from schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse,
    RefreshTokenRequest, UserResponse, UserProfileResponse,
    UpdateUsernameRequest, ChangePasswordRequest
)
from core.config import settings
from auth.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from auth.dependencies import get_current_user
from core.exceptions import APIException
from core.logging import logger

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    logger.info(f"Registration attempt for email: {request.email}")

    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == request.email.lower()))
    if existing.scalar_one_or_none():
        raise APIException(status_code=409, detail="Email already registered")

    # Create user
    user = User(
        username=request.username,
        email=request.email.lower(),
        password_hash=hash_password(request.password),
        is_active=True
    )
    db.add(user)
    await db.flush() # Populate ID

    # Generate initial tokens
    token_data = {"sub": str(user.id)}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Log registration event
    event = ActivityEvent(
        user_id=user.id,
        action_name="USER_REGISTERED",
        payload={"email": user.email}
    )
    db.add(event)
    await db.commit()

    logger.info(f"User registered successfully: {user.id}")
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    logger.info(f"Login attempt for email: {request.email}")

    result = await db.execute(select(User).where(User.email == request.email.lower(), User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise APIException(status_code=401, detail="Invalid email or password")
    
    if not user.is_active:
        raise APIException(status_code=401, detail="User account is deactivated")

    # Generate tokens
    token_data = {"sub": str(user.id)}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Log login event
    event = ActivityEvent(
        user_id=user.id,
        action_name="USER_LOGIN",
        payload={"ip_log": "N/A"}
    )
    db.add(event)
    await db.commit()

    logger.info(f"User logged in successfully: {user.id}")
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )

@router.post("/logout")
async def logout(
    request: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Log out the user by blacklisting/revoking the provided refresh token's JTI.
    """
    try:
        payload = decode_token(request.refresh_token)
        jti = payload.get("jti")
        token_type = payload.get("type")
        if not jti or token_type != "refresh":
            raise APIException(status_code=400, detail="Invalid refresh token payload")
    except jwt.PyJWTError:
        raise APIException(status_code=400, detail="Invalid refresh token")

    # Log the revocation event to blacklist this token
    revocation_event = ActivityEvent(
        user_id=current_user.id,
        action_name="TOKEN_REVOKED",
        payload={"jti": jti, "reason": "user_logout"}
    )
    db.add(revocation_event)
    await db.commit()

    logger.info(f"User {current_user.id} logged out successfully. Token {jti} revoked.")
    return {"status": "ok", "message": "Logged out successfully"}

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(request.refresh_token)
        if payload.get("type") != "refresh":
            raise APIException(status_code=401, detail="Invalid token type")
        
        user_id = payload.get("sub")
        jti = payload.get("jti")
        
        if not user_id or not jti:
            raise APIException(status_code=401, detail="Invalid token payload")
            
    except jwt.ExpiredSignatureError:
        raise APIException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise APIException(status_code=401, detail="Invalid refresh token")

    # Check if this token was already blacklisted/revoked
    stmt_revoked = select(ActivityEvent).where(
        ActivityEvent.action_name == "TOKEN_REVOKED",
        ActivityEvent.payload["jti"].astext == jti
    )
    revoked_result = await db.execute(stmt_revoked)
    if revoked_result.scalar_one_or_none():
        # Security breach: Re-use of a revoked refresh token!
        # In production, we could revoke all tokens for this user.
        logger.critical(f"Attempted reuse of revoked refresh token {jti} for user {user_id}!")
        raise APIException(status_code=401, detail="Token has been revoked")

    result = await db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise APIException(status_code=401, detail="User account is inactive or not found")

    # Revoke the old refresh token (RTR - Refresh Token Rotation)
    revocation = ActivityEvent(
        user_id=user.id,
        action_name="TOKEN_REVOKED",
        payload={"jti": jti, "reason": "token_rotated"}
    )
    db.add(revocation)

    # Issue new token pair
    token_data = {"sub": str(user.id)}
    access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token
    )

@router.get("/verify-session")
async def verify_session(current_user: User = Depends(get_current_user)):
    """Simple authenticated route to check if session access token is valid."""
    return {
        "status": "valid",
        "user_id": str(current_user.id),
        "username": current_user.username
    }

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at
    )

@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves user profile metadata, document count, and simulated storage utilization."""
    from sqlalchemy import func
    stmt = select(func.count(Document.id)).where(Document.user_id == current_user.id)
    res = await db.execute(stmt)
    total_docs = res.scalar() or 0

    # Simulated storage calculation (e.g. 128KB per document)
    storage_bytes = total_docs * 1024 * 128

    return UserProfileResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at,
        total_documents=total_docs,
        storage_used_bytes=storage_bytes
    )


@router.put("/username", response_model=UserResponse)
async def update_username(
    request: UpdateUsernameRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    current_user.username = request.username
    await db.commit()
    await db.refresh(current_user)
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at
    )

@router.put("/password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not verify_password(request.current_password, current_user.password_hash):
        raise APIException(status_code=400, detail="Incorrect current password")
    
    current_user.password_hash = hash_password(request.new_password)
    await db.commit()
    return {"status": "ok", "message": "Password updated successfully"}

