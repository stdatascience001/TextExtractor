from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt

from database.database import get_db
from models.models import User
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
        if user_id is None:
            raise APIException(status_code=401, detail="Invalid token payload")
    except jwt.ExpiredSignatureError:
        raise APIException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise APIException(status_code=401, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise APIException(status_code=401, detail="User not found")
    return user
