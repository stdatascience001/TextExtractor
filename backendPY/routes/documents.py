from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse, JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, desc, asc
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime
import os
import uuid
import csv
import io
import json
from core.config import settings

from database.database import get_db
from models.models import User, Document, DocumentResult
from schemas.document import SaveDocumentRequest, DocumentResponse, DocumentResultResponse, DocumentListResponse
from auth.dependencies import get_current_user
from core.exceptions import APIException
from core.logging import logger

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/save", response_model=DocumentResponse)
async def save_document(
    request: SaveDocumentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"Saving document '{request.file_name}' for user {current_user.id}")

    # Create document record
    doc = Document(
        user_id=current_user.id,
        file_name=request.file_name,
        file_type=request.file_type,
        file_path=request.file_path
    )
    db.add(doc)
    await db.flush()

    # Create document result record
    doc_result = DocumentResult(
        document_id=doc.id,
        full_text=request.full_text,
        structured_data=request.structured_data
    )
    db.add(doc_result)
    await db.commit()
    await db.refresh(doc)
    await db.refresh(doc_result)

    logger.info(f"Document saved with id: {doc.id}")

    return DocumentResponse(
        id=str(doc.id),
        user_id=str(doc.user_id),
        file_name=doc.file_name,
        file_type=doc.file_type,
        file_path=doc.file_path,
        created_at=str(doc.created_at),
        result=DocumentResultResponse(
            id=str(doc_result.id),
            full_text=doc_result.full_text,
            structured_data=doc_result.structured_data
        )
    )

@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    skip: int = 0,
    limit: int = 20,
    query: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Build conditions
    conditions = [Document.user_id == current_user.id]
    
    if query:
        conditions.append(Document.file_name.ilike(f"%{query}%"))
    
    if start_date:
        try:
            parsed_start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            conditions.append(Document.created_at >= parsed_start)
        except ValueError:
            pass
            
    if end_date:
        try:
            parsed_end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            conditions.append(Document.created_at <= parsed_end)
        except ValueError:
            pass

    # Build ordering
    order_col = getattr(Document, sort_by, Document.created_at)
    order_expr = desc(order_col) if sort_order == "desc" else asc(order_col)

    # Get total count
    total_result = await db.execute(
        select(func.count(Document.id)).where(and_(*conditions))
    )
    total = total_result.scalar_one()

    # Get paginated results
    result = await db.execute(
        select(Document)
        .where(and_(*conditions))
        .options(selectinload(Document.result))
        .order_by(order_expr)
        .offset(skip)
        .limit(limit)
    )
    docs = result.scalars().all()

    documents = []
    for doc in docs:
        doc_resp = DocumentResponse(
            id=str(doc.id),
            user_id=str(doc.user_id),
            file_name=doc.file_name,
            file_type=doc.file_type,
            file_path=doc.file_path,
            created_at=str(doc.created_at),
            result=DocumentResultResponse(
                id=str(doc.result.id),
                full_text=doc.result.full_text,
                structured_data=doc.result.structured_data
            ) if doc.result else None
        )
        documents.append(doc_resp)

    return DocumentListResponse(documents=documents, total=total, skip=skip, limit=limit)

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Document)
        .where(Document.id == document_id)
        .options(selectinload(Document.result))
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise APIException(status_code=404, detail="Document not found")
    if doc.user_id != current_user.id:
        raise APIException(status_code=403, detail="Not authorized to access this document")

    return DocumentResponse(
        id=str(doc.id),
        user_id=str(doc.user_id),
        file_name=doc.file_name,
        file_type=doc.file_type,
        file_path=doc.file_path,
        created_at=str(doc.created_at),
        result=DocumentResultResponse(
            id=str(doc.result.id),
            full_text=doc.result.full_text,
            structured_data=doc.result.structured_data
        ) if doc.result else None
    )

@router.delete("/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Document)
        .where(Document.id == document_id)
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise APIException(status_code=404, detail="Document not found")
    if doc.user_id != current_user.id:
        raise APIException(status_code=403, detail="Not authorized to delete this document")

    # The document result will be cascade deleted if setup, 
    # but let's delete explicitly if we need to or trust the DB cascade.
    # Actually, SQLAlchemy without cascading rules needs explicit deletion.
    res_result = await db.execute(select(DocumentResult).where(DocumentResult.document_id == document_id))
    doc_res = res_result.scalar_one_or_none()
    if doc_res:
        await db.delete(doc_res)

    await db.delete(doc)
    await db.commit()

    # Physically delete the file
    if doc.file_path.startswith("/files/"):
        filename = doc.file_path.replace("/files/", "")
        physical_path = os.path.join(settings.UPLOAD_DIR, filename)
        if os.path.exists(physical_path):
            try:
                os.remove(physical_path)
                logger.info(f"Deleted physical file: {physical_path}")
            except Exception as e:
                logger.warning(f"Failed to delete physical file {physical_path}: {str(e)}")

    return {"status": "ok", "message": "Document deleted successfully"}

@router.get("/{document_id}/export")
async def export_document(
    document_id: uuid.UUID,
    format: str = Query(..., description="Format: text, json, or csv"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Document)
        .where(Document.id == document_id)
        .options(selectinload(Document.result))
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise APIException(status_code=404, detail="Document not found")
    if doc.user_id != current_user.id:
        raise APIException(status_code=403, detail="Not authorized to access this document")
    
    if not doc.result:
        raise APIException(status_code=404, detail="Document extraction results not found")

    format = format.lower()
    base_filename = doc.file_name.rsplit('.', 1)[0] if '.' in doc.file_name else doc.file_name

    if format == "text":
        content = doc.result.full_text or ""
        return PlainTextResponse(
            content=content,
            headers={"Content-Disposition": f'attachment; filename="{base_filename}.txt"'}
        )
        
    elif format == "json":
        data = {
            "file_name": doc.file_name,
            "created_at": str(doc.created_at),
            "full_text": doc.result.full_text,
            "structured_data": doc.result.structured_data
        }
        return JSONResponse(
            content=data,
            headers={"Content-Disposition": f'attachment; filename="{base_filename}.json"'}
        )
        
    elif format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Determine how to write CSV based on structured data
        if doc.result.structured_data and isinstance(doc.result.structured_data, dict):
            # Flatten simple key-value pairs
            writer.writerow(["Key", "Value"])
            for key, value in doc.result.structured_data.items():
                if isinstance(value, (dict, list)):
                    writer.writerow([key, json.dumps(value)])
                else:
                    writer.writerow([key, str(value)])
            # Also append full text at the end for completeness
            writer.writerow([])
            writer.writerow(["Full Text", doc.result.full_text or ""])
        else:
            # Just put full text if no structured data
            writer.writerow(["Full Text"])
            writer.writerow([doc.result.full_text or ""])
            
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{base_filename}.csv"'}
        )
    
    else:
        raise APIException(status_code=400, detail="Invalid format specified. Use text, json, or csv")
