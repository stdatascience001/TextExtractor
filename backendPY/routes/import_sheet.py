import os
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, BackgroundTasks, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.database import get_db
from models.models import User, Document, ProjectMember, Project
from auth.dependencies import get_current_user
from core.config import settings
from core.exceptions import APIException
from core.logging import logger
from services.google_sheets_service import GoogleSheetsService, extract_spreadsheet_id
from services.orchestrator import run_orchestration_pipeline_with_retries

router = APIRouter()

class GoogleSheetImportRequest(BaseModel):
    sheet_url: str
    project_id: Optional[uuid.UUID] = None

@router.post("/import/google-sheet", status_code=202)
async def import_google_sheet(
    request_data: GoogleSheetImportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"--- Google Sheet Import request: {request_data.sheet_url} for user {current_user.id} ---")
    
    # Extract spreadsheet ID and fetch XLSX bytes
    try:
        spreadsheet_id = extract_spreadsheet_id(request_data.sheet_url)
        sheet_bytes = GoogleSheetsService.fetch_public_sheet_as_xlsx(request_data.sheet_url)
    except ValueError as val_err:
        raise APIException(status_code=400, detail=str(val_err))
    except Exception as err:
        logger.error(f"Google Sheet import fetch failed: {str(err)}")
        raise APIException(status_code=500, detail=f"Failed to fetch Google Sheet: {str(err)}")

    # Resolve filename and paths
    file_name = f"Google_Sheet_{spreadsheet_id[:8]}.xlsx"
    file_id = f"{uuid.uuid4()}.xlsx"
    file_path = os.path.join(settings.UPLOAD_DIR, file_id)

    # Write file to disk
    try:
        with open(file_path, "wb") as f:
            f.write(sheet_bytes)
    except Exception as io_err:
        logger.error(f"Failed to write Google Sheet to disk: {str(io_err)}")
        raise APIException(status_code=500, detail="Failed to save imported file onto server disk.")

    # Resolve project context (identical to upload.py)
    target_project_id = request_data.project_id
    if target_project_id:
        stmt = select(ProjectMember.project_id).where(
            ProjectMember.project_id == target_project_id,
            ProjectMember.user_id == current_user.id
        )
        res = await db.execute(stmt)
        if not res.scalar():
            logger.warning(f"Project {target_project_id} not found or user lacks access. Falling back to default project.")
            target_project_id = None

    if not target_project_id:
        stmt = select(ProjectMember.project_id).where(ProjectMember.user_id == current_user.id).limit(1)
        res = await db.execute(stmt)
        target_project_id = res.scalar()

        if not target_project_id:
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
        file_name=file_name,
        file_type="spreadsheet",
        file_path=f"/files/{file_id}",
        status="uploaded"
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    logger.info(f"Google Sheet Document registered with ID: {doc.id}. Queueing orchestration pipeline.")

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
            "message": "Google Sheet URL accepted and processing queued successfully.",
            "document_id": str(doc.id),
            "file_name": doc.file_name,
            "project_id": str(doc.project_id)
        }
    )
