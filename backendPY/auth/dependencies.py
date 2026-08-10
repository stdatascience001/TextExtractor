import uuid
from typing import List
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt

from database.database import get_db
from models.models import User, ProjectMember, ActivityEvent
from auth.security import decode_token
from core.exceptions import APIException

security_scheme = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    token = credentials.credentials
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise APIException(status_code=401, detail="Invalid token type")
        
        user_id = payload.get("sub")
        jti = payload.get("jti")
        
        if user_id is None or jti is None:
            raise APIException(status_code=401, detail="Invalid token payload")
            
    except jwt.ExpiredSignatureError:
        raise APIException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise APIException(status_code=401, detail="Invalid token")

    # Check token revocation/blacklist
    stmt_revoked = select(ActivityEvent).where(
        ActivityEvent.action_name == "TOKEN_REVOKED",
        ActivityEvent.payload["jti"].astext == jti
    )
    revoked_result = await db.execute(stmt_revoked)
    if revoked_result.scalar_one_or_none():
        raise APIException(status_code=401, detail="Token has been revoked")

    result = await db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
    if user is None:
        raise APIException(status_code=401, detail="User not found")
    if not user.is_active:
        raise APIException(status_code=401, detail="User is deactivated")
        
    return user

def require_project_member(db: AsyncSession = Depends(get_db)):
    """Dynamic check to ensure the user belongs to the project."""
    async def dependency(
        project_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> ProjectMember:
        stmt = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user.id
        )
        res = await db.execute(stmt)
        member = res.scalar_one_or_none()
        if not member:
            raise HTTPException(status_code=403, detail="Not a member of this project")
        return member
    return dependency

def require_project_role(allowed_roles: List[str]):
    """Dynamic role check dependency injection guard."""
    async def dependency(
        project_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> ProjectMember:
        stmt = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user.id
        )
        res = await db.execute(stmt)
        member = res.scalar_one_or_none()
        if not member:
            raise HTTPException(status_code=403, detail="Not a member of this project")
        if member.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient project permissions")
        return member
    return dependency

