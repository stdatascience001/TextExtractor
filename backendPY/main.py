import os
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.config import settings
from core.logging import logger
from core.exceptions import register_exception_handlers
from routes import upload, health, auth, documents, projects, facts

# Ensure Docling is installed
try:
    import docling
    logger.info("Docling is already installed and verified.")
except ImportError:
    logger.warning("Docling not detected in python environment. Executing programmatic pip install...")
    try:
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "docling"])
        logger.info("Docling successfully installed programmatically.")
    except Exception as pip_err:
        logger.error(f"Failed to programmatically install Docling: {str(pip_err)}")

app = FastAPI(
    title=settings.APP_NAME,
    description="DocExtract document parsing and text extraction service",
    version="1.0.0"
)

# CORS configuration — in development, allow all origins to prevent
# IPv4/IPv6/localhost/127.0.0.1 mismatch stalls on Windows
_is_dev = settings.APP_ENV.lower() in ("development", "dev", "local")
_cors_origins = ["*"] if _is_dev else settings.cors_origins_list

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=not _is_dev,  # credentials require explicit origins
    allow_methods=["*"],
    allow_headers=["*"],
)

# Central exception handling
register_exception_handlers(app)

# Mount files static folder
app.mount("/files", StaticFiles(directory=settings.UPLOAD_DIR), name="files")

# API Versioning: V1 Router
api_v1_router = APIRouter()
api_v1_router.include_router(upload.router, tags=["upload"])
api_v1_router.include_router(health.router, tags=["health"])
api_v1_router.include_router(auth.router, tags=["auth"])
api_v1_router.include_router(documents.router, tags=["documents"])
api_v1_router.include_router(projects.router, tags=["projects"])
api_v1_router.include_router(facts.router, tags=["facts"])

app.include_router(api_v1_router, prefix=settings.API_V1_STR)

# Backward compatibility routes for frontend (which expects root endpoints)
app.include_router(upload.router, tags=["compatibility"])
app.include_router(health.router, tags=["compatibility"])
app.include_router(auth.router, tags=["compatibility"])
app.include_router(documents.router, tags=["compatibility"])
app.include_router(projects.router, tags=["compatibility"])
app.include_router(facts.router, tags=["compatibility"])

# Health check also at root
@app.get("/")
async def root():
    return {"status": "ok", "message": "PDF Reader API is running"}

@app.on_event("startup")
async def startup_event():
    from database.base import Base
    from database.database import engine, SessionLocal
    from utils.db_migrator import run_auto_migrations
    from models.models import Document
    from sqlalchemy import update
    from datetime import datetime, timezone
    
    try:
        # 1. Run migrations for missing columns on existing tables (schema drift)
        await run_auto_migrations(engine)
        
        # 2. Create any completely new tables
        logger.info(f"Allowed CORS Origins: {settings.cors_origins_list}")
        logger.info("Initializing database schemas and checking for missing tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schemas verified successfully.")
        
        # 3. Clean up stuck transient document states from prior runs
        async with SessionLocal() as session:
            stmt = (
                update(Document)
                .where(Document.status.in_([
                    "ocr_running",
                    "chunking_running",
                    "embedding_running",
                    "extraction_running",
                    "conflict_running",
                    "clarification_running",
                    "ready_for_validation"
                ]))
                .values(status="failed", updated_at=datetime.now(timezone.utc))
            )
            await session.execute(stmt)
            await session.commit()
        logger.info("Cleaned up any orphaned document statuses from previous server processes.")
    except Exception as db_err:
        logger.error(f"Error during database schema synchronization: {str(db_err)}")

    from services.outbox_worker import worker_instance
    from services.embedding_worker import embedding_worker_instance
    worker_instance.start()
    embedding_worker_instance.start()

@app.on_event("shutdown")
async def shutdown_event():
    from services.outbox_worker import worker_instance
    from services.embedding_worker import embedding_worker_instance
    await worker_instance.stop()
    await embedding_worker_instance.stop()
