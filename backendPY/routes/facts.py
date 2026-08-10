import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from database.database import get_db
from models.models import User
from auth.dependencies import get_current_user
from services.review_service import KnowledgeReviewService

router = APIRouter(prefix="/facts", tags=["facts"])

class FactModifyRequest(BaseModel):
    predicate: str
    object_text: str

def format_fact_response(fact) -> dict:
    return {
        "id": str(fact.id),
        "project_id": str(fact.project_id),
        "subject_id": str(fact.subject_id),
        "predicate": fact.predicate,
        "object_text": fact.object_text,
        "confidence": fact.confidence,
        "status": fact.status,
        "updated_at": fact.updated_at.isoformat() if fact.updated_at else None
    }

@router.post("/{fact_id}/approve")
async def approve_fact(
    fact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Approves an extracted fact claim, verifying its status and logging the audit."""
    try:
        fact = await KnowledgeReviewService.approve_fact(db, fact_id, current_user.id)
        return format_fact_response(fact)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to approve fact: {str(e)}")

@router.post("/{fact_id}/reject")
async def reject_fact(
    fact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Rejects an extracted fact claim, soft-deleting it and updating its status."""
    try:
        fact = await KnowledgeReviewService.reject_fact(db, fact_id, current_user.id)
        return format_fact_response(fact)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reject fact: {str(e)}")

@router.post("/{fact_id}/modify")
async def modify_fact(
    fact_id: uuid.UUID,
    request: FactModifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Modifies a fact claim with new predicate/object values and updates verification states."""
    try:
        fact = await KnowledgeReviewService.modify_fact(
            db=db,
            fact_id=fact_id,
            user_id=current_user.id,
            new_predicate=request.predicate,
            new_object_text=request.object_text
        )
        return format_fact_response(fact)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to modify fact: {str(e)}")

@router.post("/{fact_id}/undo")
async def undo_fact_action(
    fact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reverts the last verification review action (Approve/Reject/Modify) on a fact."""
    try:
        fact = await KnowledgeReviewService.undo_last_action(db, fact_id, current_user.id)
        return format_fact_response(fact)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to undo last fact action: {str(e)}")

@router.get("/{fact_id}/history")
async def get_fact_history(
    fact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves the complete modification and verification history logs for a fact."""
    from sqlalchemy import select
    from models.models import ActivityEvent
    
    stmt = (
        select(ActivityEvent)
        .where(ActivityEvent.action_name.in_(["FACT_APPROVED", "FACT_REJECTED", "FACT_MODIFIED", "FACT_ACTION_UNDONE"]))
        .order_by(ActivityEvent.created_at.desc())
    )
    res = await db.execute(stmt)
    events = res.scalars().all()
    
    history = []
    for ev in events:
        if ev.payload and ev.payload.get("fact_id") == str(fact_id):
            history.append({
                "id": str(ev.id),
                "action_name": ev.action_name,
                "payload": ev.payload,
                "created_at": ev.created_at.isoformat() if ev.created_at else None
            })
            
    return history
