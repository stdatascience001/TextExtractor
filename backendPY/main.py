import os
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.config import settings
from core.logging import logger
from core.exceptions import register_exception_handlers
from routes import upload, health, auth, documents

# Ensure the upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title=settings.APP_NAME,
    description="DocExtract document parsing and text extraction service",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
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

app.include_router(api_v1_router, prefix=settings.API_V1_STR)

# Backward compatibility routes for frontend (which expects root endpoints)
app.include_router(upload.router, tags=["compatibility"])
app.include_router(health.router, tags=["compatibility"])
app.include_router(auth.router, tags=["compatibility"])
app.include_router(documents.router, tags=["compatibility"])

# Health check also at root
@app.get("/")
async def root():
    return {"status": "ok", "message": "PDF Reader API is running"}
