import os
import uuid
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.database import get_db
from models.models import User, Document, ProjectMember, Project
from auth.dependencies import get_current_user
from core.config import settings
from core.exceptions import APIException
from core.logging import logger
from utils.validation import validate_file

from services.orchestrator import run_orchestration_pipeline_with_retries

router = APIRouter()

@router.post("/upload", status_code=202)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_id: Optional[uuid.UUID] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"--- Received upload: {file.filename} for user {current_user.id} ---")
    ext = validate_file(file)

    contents = await file.read()
    if len(contents) > settings.MAX_FILE_SIZE:
        raise APIException(
            status_code=422,
            detail=f"File size exceeds {settings.MAX_FILE_SIZE // (1024 * 1024)}MB limit"
        )

    file_id = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, file_id)

    # Write file to disk
    with open(file_path, "wb") as f:
        f.write(contents)

    # Resolve file type mapping
    if ext == "pdf":
        file_type = "pdf"
    elif ext in ("jpg", "jpeg", "png"):
        file_type = "image"
    elif ext == "docx":
        file_type = "docx"
    elif ext in ("txt", "csv"):
        file_type = "text"
    else:
        file_type = "unknown"

    # Resolve project context
    target_project_id = project_id
    if not target_project_id:
        stmt = select(ProjectMember.project_id).where(ProjectMember.user_id == current_user.id).limit(1)
        res = await db.execute(stmt)
        target_project_id = res.scalar()

        if not target_project_id:
            # Create a default workspace if none exists
            new_project = Project(
                id=uuid.uuid4(),
                name=f"{current_user.username}'s Personal Workspace",
                description="Default workspace created automatically during document upload."
            )
            db.add(new_project)
            
            member = ProjectMember(
                project_id=new_project.id,
                user_id=current_user.id,
                role="owner"
            )
            db.add(member)
            await db.flush()
            target_project_id = new_project.id

    # Create document record
    doc = Document(
        project_id=target_project_id,
        user_id=current_user.id,
        file_name=file.filename,
        file_type=file_type,
        file_path=f"/files/{file_id}",
        status="uploaded"
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    logger.info(f"Document registered in database with ID: {doc.id}. Queueing orchestration pipeline.")

    # Queue background task
    background_tasks.add_task(
        run_orchestration_pipeline_with_retries,
        db,
        doc.id,
        file_path
    )

    return JSONResponse(
        status_code=202,
        content={
            "status": "accepted",
            "message": "Document uploaded and processing queued successfully.",
            "document_id": str(doc.id),
            "file_name": doc.file_name,
            "project_id": str(doc.project_id)
        }
    )
