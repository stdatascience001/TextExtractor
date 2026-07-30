from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt

from database.database import get_db
from models.models import User
from schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse,
    RefreshTokenRequest, UserResponse, UserProfileResponse,
    UpdateUsernameRequest, ChangePasswordRequest
)
import os
from core.config import settings
from models.models import Document, DocumentResult
from auth.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from auth.dependencies import get_current_user
from core.exceptions import APIException
from core.logging import logger

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    logger.info(f"Registration attempt for email: {request.email}")

    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == request.email))
    if existing.scalar_one_or_none():
        raise APIException(status_code=409, detail="Email already registered")

    # Create user
    user = User(
        username=request.username,
        email=request.email,
        password_hash=hash_password(request.password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"User registered successfully: {user.id}")

    # Generate tokens
    token_data = {"sub": str(user.id)}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data)
    )

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    logger.info(f"Login attempt for email: {request.email}")

    result = await db.execute(select(User).where(User.email == request.email.lower()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise APIException(status_code=401, detail="Invalid email or password")

    logger.info(f"User logged in: {user.id}")

    token_data = {"sub": str(user.id)}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data)
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(request.refresh_token)
        if payload.get("type") != "refresh":
            raise APIException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
    except jwt.ExpiredSignatureError:
        raise APIException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise APIException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise APIException(status_code=401, detail="User not found")

    token_data = {"sub": str(user.id)}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data)
    )

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        created_at=str(current_user.created_at)
    )

@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get all documents for the user
    result = await db.execute(select(Document).where(Document.user_id == current_user.id))
    docs = result.scalars().all()
    
    total_documents = len(docs)
    storage_used = 0
    
    for doc in docs:
        if doc.file_path.startswith("/files/"):
            filename = doc.file_path.replace("/files/", "")
            physical_path = os.path.join(settings.UPLOAD_DIR, filename)
            if os.path.exists(physical_path):
                storage_used += os.path.getsize(physical_path)

    return UserProfileResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        created_at=str(current_user.created_at),
        total_documents=total_documents,
        storage_used_bytes=storage_used
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
        created_at=str(current_user.created_at)
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

@router.delete("/me")
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Fetch all documents
    result = await db.execute(select(Document).where(Document.user_id == current_user.id))
    docs = result.scalars().all()

    # 2. Delete physical files
    for doc in docs:
        if doc.file_path.startswith("/files/"):
            filename = doc.file_path.replace("/files/", "")
            physical_path = os.path.join(settings.UPLOAD_DIR, filename)
            if os.path.exists(physical_path):
                try:
                    os.remove(physical_path)
                except Exception as e:
                    logger.warning(f"Failed to delete physical file {physical_path} during account deletion: {str(e)}")

    # 3. Delete DocumentResults and Documents
    # We will do this explicitly to avoid foreign key errors if cascade is not fully configured
    doc_ids = [doc.id for doc in docs]
    if doc_ids:
        # Delete document results
        await db.execute(DocumentResult.__table__.delete().where(DocumentResult.document_id.in_(doc_ids)))
        # Delete documents
        await db.execute(Document.__table__.delete().where(Document.user_id == current_user.id))

    # 4. Delete the User
    await db.execute(User.__table__.delete().where(User.id == current_user.id))
    await db.commit()

    logger.info(f"Account deleted successfully: {current_user.id}")
    return {"status": "ok", "message": "Account deleted successfully"}
