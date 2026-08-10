from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import os

from database.database import get_db
from core.config import settings

router = APIRouter(tags=["health"])

@router.get("/health/liveness")
async def liveness_check():
    """Liveness check confirming container processes are online."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.5)
    db_port_status = "unknown"
    try:
        s.connect(("127.0.0.1", 5432))
        db_port_status = "open"
        s.close()
    except Exception as e:
        db_port_status = f"closed: {str(e)}"
        
    return {"status": "ok", "state": "alive", "db_port_status": db_port_status}


@router.get("/health/readiness")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness check confirming active DB connection and file system writes."""
    # 1. Verify DB connection is healthy
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unresponsive: {str(e)}")

    # 2. Verify Storage path is writeable
    try:
        test_file = os.path.join(settings.UPLOAD_DIR, ".healthcheck")
        with open(test_file, "w") as f:
            f.write("ready")
        os.remove(test_file)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Upload directory write lock fail: {str(e)}")

    return {"status": "ok", "state": "ready"}













