import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body

logger = logging.getLogger("projects")
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.database import get_db
from models.models import User, ProjectMember
from auth.dependencies import get_current_user, require_project_member, require_project_role
from services.project_service import ProjectService
from domain.value_objects.project_role import ProjectRole
from infrastructure.persistence.repositories.uow import SQLAlchemyUnitOfWork
from schemas.project import (
    ProjectCreateSchema, ProjectUpdateSchema,
    ProjectResponseSchema, ProjectDetailResponseSchema,
    MemberAddSchema, MemberUpdateSchema, MemberResponseSchema
)

router = APIRouter(prefix="/projects", tags=["projects"])

async def get_uow(db: AsyncSession = Depends(get_db)) -> SQLAlchemyUnitOfWork:
    return SQLAlchemyUnitOfWork(db)

@router.post("", response_model=ProjectResponseSchema)
async def create_project(
    request: ProjectCreateSchema,
    current_user: User = Depends(get_current_user),
    uow: SQLAlchemyUnitOfWork = Depends(get_uow)
):
    project = await ProjectService.create_project(uow, current_user.id, request)
    return project

@router.get("", response_model=List[ProjectResponseSchema])
async def list_projects(
    current_user: User = Depends(get_current_user),
    uow: SQLAlchemyUnitOfWork = Depends(get_uow)
):
    projects = await ProjectService.get_projects_for_user(uow, current_user.id)
    return projects

@router.get("/{project_id}", response_model=ProjectDetailResponseSchema)
async def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    member: ProjectMember = Depends(require_project_member()),
    uow: SQLAlchemyUnitOfWork = Depends(get_uow)
):
    # Fetch details and members list
    project, members = await ProjectService.get_project_details(uow, project_id)
    return ProjectDetailResponseSchema(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        members=members
    )

@router.put("/{project_id}", response_model=ProjectResponseSchema)
async def update_project(
    project_id: uuid.UUID,
    request: ProjectUpdateSchema,
    current_user: User = Depends(get_current_user),
    member: ProjectMember = Depends(require_project_role(["owner", "admin"])),
    uow: SQLAlchemyUnitOfWork = Depends(get_uow)
):
    project = await ProjectService.update_project(uow, project_id, request)
    return project

@router.delete("/{project_id}")
async def delete_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    member: ProjectMember = Depends(require_project_role(["owner"])),
    uow: SQLAlchemyUnitOfWork = Depends(get_uow)
):
    await ProjectService.delete_project(uow, project_id, current_user.id)
    return {"status": "ok", "message": "Project deleted successfully"}

# 5. Add GET /projects/{project_id}/members with pagination
@router.get("/{project_id}/members", response_model=List[MemberResponseSchema])
async def list_project_members(
    project_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    member: ProjectMember = Depends(require_project_member()),
    uow: SQLAlchemyUnitOfWork = Depends(get_uow)
):
    _, members = await ProjectService.get_project_details(uow, project_id)
    # Apply pagination slice
    return members[skip : skip + limit]

@router.post("/{project_id}/members")
async def add_or_invite_member(
    project_id: uuid.UUID,
    request: MemberAddSchema,
    current_user: User = Depends(get_current_user),
    member: ProjectMember = Depends(require_project_role(["owner", "admin"])),
    uow: SQLAlchemyUnitOfWork = Depends(get_uow)
):
    # Enforce role bounds: only owner can add admins or other owners
    if request.role in [ProjectRole.OWNER.value, ProjectRole.ADMIN.value] and member.role != ProjectRole.OWNER.value:
        raise HTTPException(status_code=403, detail="Only project owners can add owners or admins")

    result = await ProjectService.add_or_invite_member(uow, project_id, request, current_user.id, uow.session)
    return result

# 6. Replace PUT role update endpoint with PATCH
@router.patch("/{project_id}/members/{target_user_id}")
async def update_member_role(
    project_id: uuid.UUID,
    target_user_id: uuid.UUID,
    request: MemberUpdateSchema,
    current_user: User = Depends(get_current_user),
    member: ProjectMember = Depends(require_project_role(["owner"])),
    uow: SQLAlchemyUnitOfWork = Depends(get_uow)
):
    try:
        role_enum = ProjectRole(request.role.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role value: {request.role}")

    await ProjectService.update_member_role(uow, project_id, target_user_id, role_enum, current_user.id)
    return {"status": "ok", "message": "Member role updated successfully"}

@router.delete("/{project_id}/members/{target_user_id}")
async def remove_member(
    project_id: uuid.UUID,
    target_user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    member: ProjectMember = Depends(require_project_role(["owner", "admin"])),
    uow: SQLAlchemyUnitOfWork = Depends(get_uow)
):
    # Admins cannot remove owners or other admins, only owner can
    if member.role == ProjectRole.ADMIN.value:
        target_member = await uow.members.get_member(project_id, target_user_id)
        if target_member and target_member.role in [ProjectRole.OWNER.value, ProjectRole.ADMIN.value]:
            raise HTTPException(status_code=403, detail="Project admins cannot remove owners or other admins")

    await ProjectService.remove_member(uow, project_id, target_user_id, current_user.id)
    return {"status": "ok", "message": "Member removed from project successfully"}


from pydantic import BaseModel

class AskAssistantRequest(BaseModel):
    question: str


@router.post("/{project_id}/assistant")
async def ask_assistant(
    project_id: uuid.UUID,
    request: AskAssistantRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Answers patient questions using semantic search and verified LLM context reasoning."""
    from services.search_service import HybridSearchEngine
    from services.llm_service import ResilientLLMService
    from domain.value_objects.llm import LLMSettings

    # 1. Fetch relevant chunks using hybrid search
    chunks = await HybridSearchEngine.search(
        db=db,
        project_id=project_id,
        query_text=request.question,
        top_k=3
    )

    context_text = "\n\n".join([f"Source Context [Doc: {c['citation']['document_name']}, Page: {c['citation']['page_number']}]:\n{c['content']}" for c in chunks])

    # 2. Build prompt context
    sys_prompt = "You are a helpful AI medical platform assistant. Answer the user's question using the provided source context only."
    user_prompt = (
        f"Context:\n{context_text}\n\n"
        f"Question: {request.question}\n\n"
        f"Provide a clear, detailed clinical response referencing sources when possible."
    )
    prompt = f"System Prompt:\n{sys_prompt}\n\nUser Message:\n{user_prompt}"

    # 3. Call reasoning engine
    llm_service = ResilientLLMService(db)
    settings = LLMSettings(
        temperature=0.2,
        project_id=project_id,
        user_id=current_user.id
    )

    response = await llm_service.generate("reasoning-heavy", prompt, settings)

    return {
        "answer": response.content,
        "sources": [
            {
                "document_name": c["citation"]["document_name"],
                "page_number": c["citation"]["page_number"],
                "text_snippet": c["content"][:200]
            } for c in chunks
        ]
    }


@router.get("/{project_id}/graph")
async def get_knowledge_graph(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves active project nodes and verified relationships for graph visualizations."""
    from models.models import KnowledgeEntity, Fact
    from sqlalchemy import and_

    # Get active entities
    ent_stmt = select(KnowledgeEntity).where(
        and_(
            KnowledgeEntity.project_id == project_id,
            KnowledgeEntity.deleted_at.is_(None)
        )
    )
    ent_res = await db.execute(ent_stmt)
    entities = ent_res.scalars().all()

    # Get active facts
    fact_stmt = select(Fact).where(
        and_(
            Fact.project_id == project_id,
            Fact.deleted_at.is_(None)
        )
    )
    fact_res = await db.execute(fact_stmt)
    facts = fact_res.scalars().all()

    nodes = [
        {
            "id": str(e.id),
            "label": e.name,
            "type": e.entity_type,
            "description": e.description
        } for e in entities
    ]

    edges = [
        {
            "id": str(f.id),
            "source": str(f.subject_id),
            "target": f.object_text, # Fact object value serves as relation node targets
            "label": f.predicate,
            "status": f.status,
            "confidence": f.confidence
        } for f in facts
    ]

    return {"nodes": nodes, "edges": edges}


async def get_fact_details(db: AsyncSession, fact_id: uuid.UUID) -> dict:
    from models.models import Fact, KnowledgeEntity, Evidence, Chunk, Page, Document
    from sqlalchemy.orm import selectinload

    # Fetch Fact with Subject KnowledgeEntity
    stmt = (
        select(Fact)
        .options(selectinload(Fact.subject))
        .where(Fact.id == fact_id)
    )
    res = await db.execute(stmt)
    fact = res.scalar_one_or_none()
    if not fact:
        return {}

    subject_name = fact.subject.name if fact.subject else "Unknown"
    subject_type = fact.subject.entity_type if fact.subject else "Unknown"

    # Fetch evidence and document details
    evidence_stmt = (
        select(Evidence, Document)
        .join(Chunk, Evidence.chunk_id == Chunk.id)
        .join(Page, Chunk.page_id == Page.id)
        .join(Document, Page.document_id == Document.id)
        .where(Evidence.fact_id == fact_id)
    )
    evidence_res = await db.execute(evidence_stmt)
    evidence_row = evidence_res.first()
    
    source_doc = "Unknown Document"
    evidence_verbatim = ""
    if evidence_row:
        evidence_obj, doc_obj = evidence_row
        source_doc = doc_obj.filename
        evidence_verbatim = evidence_obj.bounding_box.get("verbatim", "") if isinstance(evidence_obj.bounding_box, dict) else ""

    return {
        "id": str(fact.id),
        "subject_name": subject_name,
        "subject_type": subject_type,
        "predicate": fact.predicate,
        "object_text": fact.object_text,
        "confidence": fact.confidence,
        "status": fact.status,
        "source_doc": source_doc,
        "evidence_verbatim": evidence_verbatim
    }

@router.get("/{project_id}/conflicts")
async def list_project_conflicts(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lists active and resolved contradiction conflicts in the project workspace."""
    from models.models import ConflictReport
    import asyncio

    stmt = select(ConflictReport).where(ConflictReport.project_id == project_id).order_by(ConflictReport.created_at.desc())
    res = await db.execute(stmt)
    reports = res.scalars().all()

    async def get_report_payload(r):
        first_details = await get_fact_details(db, r.first_fact_id)
        second_details = await get_fact_details(db, r.second_fact_id)
        return {
            "id": str(r.id),
            "first_fact_id": str(r.first_fact_id),
            "second_fact_id": str(r.second_fact_id),
            "status": r.status,
            "conflict_type": getattr(r, 'conflict_type', 'contradiction'),
            "confidence_score": getattr(r, 'confidence_score', 0.90),
            "llm_model": getattr(r, 'llm_model', 'groq/llama3'),
            "reasoning": getattr(r, 'reasoning', r.resolution_notes),
            "resolution_notes": r.resolution_notes,
            "resolved_by": str(r.resolved_by) if r.resolved_by else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "first_fact": first_details,
            "second_fact": second_details
        }
        
    payloads = await asyncio.gather(*(get_report_payload(r) for r in reports))
    return payloads


@router.get("/{project_id}/reports")
async def list_generated_reports(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves metadata references of generated document summaries and letters."""
    from models.models import GeneratedDocument
    from sqlalchemy import and_

    stmt = select(GeneratedDocument).where(GeneratedDocument.project_id == project_id).order_by(GeneratedDocument.created_at.desc())
    res = await db.execute(stmt)
    docs = res.scalars().all()

    return [
        {
            "id": str(d.id),
            "name": d.name,
            "file_path": d.file_path,
            "created_by": str(d.created_by),
            "created_at": d.created_at.isoformat() if d.created_at else None
        } for d in docs
    ]


@router.get("/{project_id}/facts/review")
async def list_facts_for_review(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lists active project claims, helping human reviewers check verification status."""
    from models.models import Fact, KnowledgeEntity, Evidence, Chunk, Page, Document
    from sqlalchemy.orm import selectinload
    from sqlalchemy import and_

    stmt = (
        select(Fact)
        .options(
            selectinload(Fact.subject),
            selectinload(Fact.evidence)
            .selectinload(Evidence.chunk)
            .selectinload(Chunk.page)
            .selectinload(Page.document)
        )
        .where(
            and_(
                Fact.project_id == project_id,
                Fact.deleted_at.is_(None)
            )
        )
        .order_by(Fact.created_at.desc())
    )
    res = await db.execute(stmt)
    facts = res.scalars().all()

    payloads = []
    for f in facts:
        evidence_list = []
        for ev in f.evidence:
            if ev.chunk and ev.chunk.page and ev.chunk.page.document:
                evidence_list.append({
                    "id": str(ev.id),
                    "chunk_id": str(ev.chunk_id),
                    "document_name": ev.chunk.page.document.file_name,
                    "page_number": ev.chunk.page.page_number,
                    "text_snippet": ev.chunk.content[:200]
                })

        payloads.append({
            "id": str(f.id),
            "subject": {
                "id": str(f.subject.id) if f.subject else None,
                "name": f.subject.name if f.subject else "Unknown",
                "type": f.subject.entity_type if f.subject else "entity"
            },
            "predicate": f.predicate,
            "object": f.object_text,
            "confidence": f.confidence,
            "status": f.status,
            "evidence": evidence_list,
            "created_at": f.created_at.isoformat() if f.created_at else None
        })
    return payloads

class BatchApproveRequest(BaseModel):
    fact_ids: list[uuid.UUID]

@router.post("/{project_id}/facts/batch-approve")
async def batch_approve_facts(
    project_id: uuid.UUID,
    req: BatchApproveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Approves a batch of fact IDs, transitioning them to verified and updating search indexes."""
    from services.review_service import KnowledgeReviewService
    
    for fid in req.fact_ids:
        try:
            await KnowledgeReviewService.approve_fact(db, fid, current_user.id)
        except Exception:
            pass
            
    return {"status": "ok", "message": f"Successfully processed approval for {len(req.fact_ids)} claims"}


@router.get("/{project_id}/dashboard")
async def get_project_dashboard(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Summarizes status counters (verified facts, pending queries, reports) for the project dashboard."""
    from models.models import KnowledgeEntity, Fact, ConflictReport, ClarificationQuestion, GeneratedDocument
    from sqlalchemy import and_, func

    # Entities count
    ent_count = await db.scalar(
        select(func.count(KnowledgeEntity.id)).where(
            and_(
                KnowledgeEntity.project_id == project_id,
                KnowledgeEntity.deleted_at.is_(None)
            )
        )
    )

    # Verified facts count
    verified_count = await db.scalar(
        select(func.count(Fact.id)).where(
            and_(
                Fact.project_id == project_id,
                Fact.status == "verified",
                Fact.deleted_at.is_(None)
            )
        )
    )

    # Unverified facts count
    unverified_count = await db.scalar(
        select(func.count(Fact.id)).where(
            and_(
                Fact.project_id == project_id,
                Fact.status == "unverified",
                Fact.deleted_at.is_(None)
            )
        )
    )

    # Active conflicts count
    conflict_count = await db.scalar(
        select(func.count(ConflictReport.id)).where(
            and_(
                ConflictReport.project_id == project_id,
                ConflictReport.status.in_(["active", "open"])
            )
        )
    )

    # Pending clarification questions
    clarification_count = await db.scalar(
        select(func.count(ClarificationQuestion.id)).where(
            and_(
                ClarificationQuestion.project_id == project_id,
                ClarificationQuestion.answer.is_(None)
            )
        )
    )

    # Generated documents count
    report_count = await db.scalar(
        select(func.count(GeneratedDocument.id)).where(
            GeneratedDocument.project_id == project_id
        )
    )

    return {
        "project_id": str(project_id),
        "metrics": {
            "total_entities": ent_count or 0,
            "verified_facts": verified_count or 0,
            "unverified_facts": unverified_count or 0,
            "active_conflicts": conflict_count or 0,
            "pending_clarifications": clarification_count or 0,
            "generated_reports": report_count or 0
        }
    }

from pydantic import BaseModel
from datetime import datetime, timezone

class ConflictResolveRequest(BaseModel):
    resolving_fact_id: uuid.UUID

class ConflictMergeRequest(BaseModel):
    merged_predicate: str
    merged_value: str

@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_project_conflict(
    conflict_id: uuid.UUID,
    req: ConflictResolveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from services.conflict_service import KnowledgeConflictDetector
    from services.llm_service import ResilientLLMService
    llm_service = ResilientLLMService()
    detector = KnowledgeConflictDetector(llm_service)
    try:
        await detector.resolve_conflict(db, conflict_id, req.resolving_fact_id, current_user.id)
        return {"status": "ok", "message": "Conflict resolved successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conflicts/{conflict_id}/ignore")
async def ignore_project_conflict(
    conflict_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from models.models import ConflictReport, Fact, ActivityEvent
    async with db.begin_nested():
        stmt = select(ConflictReport).where(ConflictReport.id == conflict_id)
        res = await db.execute(stmt)
        report = res.scalar_one_or_none()
        if not report:
            raise HTTPException(status_code=404, detail="Conflict report not found")
        
        report.status = "ignored"
        report.resolved_by = current_user.id
        report.updated_at = datetime.now(timezone.utc)
        
        # Restore both facts status to verified
        fact_a = (await db.execute(select(Fact).where(Fact.id == report.first_fact_id))).scalar_one_or_none()
        fact_b = (await db.execute(select(Fact).where(Fact.id == report.second_fact_id))).scalar_one_or_none()
        if fact_a:
            fact_a.status = "verified"
        if fact_b:
            fact_b.status = "verified"
            
        event = ActivityEvent(
            user_id=current_user.id,
            project_id=report.project_id,
            action_name="CONFLICT_IGNORED",
            payload={
                "conflict_report_id": str(conflict_id),
                "ignored_by_user_id": str(current_user.id)
            }
        )
        db.add(event)
    await db.commit()
    return {"status": "ok", "message": "Conflict ignored successfully"}

@router.post("/conflicts/{conflict_id}/merge")
async def merge_project_conflict(
    conflict_id: uuid.UUID,
    req: ConflictMergeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from models.models import ConflictReport, Fact, ActivityEvent, Evidence
    async with db.begin_nested():
        stmt = select(ConflictReport).where(ConflictReport.id == conflict_id)
        res = await db.execute(stmt)
        report = res.scalar_one_or_none()
        if not report:
            raise HTTPException(status_code=404, detail="Conflict report not found")
        
        # Retrieve facts
        fact_a = (await db.execute(select(Fact).where(Fact.id == report.first_fact_id))).scalar_one_or_none()
        fact_b = (await db.execute(select(Fact).where(Fact.id == report.second_fact_id))).scalar_one_or_none()
        if not fact_a or not fact_b:
            raise HTTPException(status_code=400, detail="Conflicting parent facts missing")
            
        # Create a new merged fact
        merged_fact = Fact(
            project_id=report.project_id,
            subject_id=fact_a.subject_id,
            predicate=req.merged_predicate,
            object_text=req.merged_value,
            confidence=1.0,
            status="verified"
        )
        db.add(merged_fact)
        await db.flush()
        
        # Link evidence to the merged fact
        for old_fact in [fact_a, fact_b]:
            evidence_stmt = select(Evidence).where(Evidence.fact_id == old_fact.id)
            evidences = (await db.execute(evidence_stmt)).scalars().all()
            for ev in evidences:
                # Associate evidence with the new merged fact
                new_ev = Evidence(
                    fact_id=merged_fact.id,
                    chunk_id=ev.chunk_id,
                    bounding_box=ev.bounding_box
                )
                db.add(new_ev)
            
            # Soft delete old facts
            old_fact.deleted_at = datetime.now(timezone.utc)
            old_fact.status = "superseded"
            
        report.status = "resolved"
        report.resolved_by = current_user.id
        report.updated_at = datetime.now(timezone.utc)
        
        event = ActivityEvent(
            user_id=current_user.id,
            project_id=report.project_id,
            action_name="CONFLICT_RESOLVED",
            payload={
                "conflict_report_id": str(conflict_id),
                "merged_fact_id": str(merged_fact.id),
                "resolved_by_user_id": str(current_user.id)
            }
        )
        db.add(event)
    return {"status": "ok", "message": "Conflict merged successfully"}

@router.get("/{project_id}/clarifications")
async def list_project_clarifications(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lists all clarification questions generated inside the project workspace."""
    from models.models import ClarificationQuestion
    from sqlalchemy.orm import selectinload
    import json
    
    stmt = (
        select(ClarificationQuestion)
        .options(
            selectinload(ClarificationQuestion.fact),
            selectinload(ClarificationQuestion.entity)
        )
        .where(ClarificationQuestion.project_id == project_id)
        .order_by(ClarificationQuestion.created_at.desc())
    )
    res = await db.execute(stmt)
    questions = res.scalars().all()

    payloads = []
    for q in questions:
        try:
            q_detail = json.loads(q.question)
        except Exception:
            q_detail = {
                "question": q.question,
                "reason": q.trigger_type,
                "evidence": "",
                "priority": "medium",
                "suggested_answer_type": "text",
                "choices": None
            }

        payloads.append({
            "id": str(q.id),
            "project_id": str(q.project_id),
            "document_id": str(q.document_id) if q.document_id else None,
            "question_data": q_detail,
            "answer": q.answer,
            "status": q.status,
            "trigger_type": q.trigger_type,
            "fact_id": str(q.fact_id) if q.fact_id else None,
            "entity_id": str(q.entity_id) if q.entity_id else None,
            "fact": {
                "id": str(q.fact.id),
                "predicate": q.fact.predicate,
                "object_text": q.fact.object_text,
                "confidence": q.fact.confidence,
                "status": q.fact.status
            } if q.fact else None,
            "entity": {
                "id": str(q.entity.id),
                "name": q.entity.name,
                "entity_type": q.entity.entity_type
            } if q.entity else None,
            "resolved_by": str(q.resolved_by) if q.resolved_by else None,
            "created_at": q.created_at.isoformat() if q.created_at else None,
            "updated_at": q.updated_at.isoformat() if q.updated_at else None
        })
    return payloads

class AnswerQuestionRequest(BaseModel):
    answer: str

@router.post("/clarifications/{question_id}/answer")
async def answer_project_clarification(
    question_id: uuid.UUID,
    req: AnswerQuestionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from services.clarification_service import KnowledgeClarificationEngine
    from services.llm_service import ResilientLLMService
    
    llm_service = ResilientLLMService()
    engine = KnowledgeClarificationEngine(llm_service)
    try:
        await engine.resolve_question(db, question_id, req.answer, current_user.id)
        return {"status": "ok", "message": "Clarification question answered successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clarifications/{question_id}/dismiss")
async def dismiss_project_clarification(
    question_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from services.clarification_service import KnowledgeClarificationEngine
    from services.llm_service import ResilientLLMService
    
    llm_service = ResilientLLMService()
    engine = KnowledgeClarificationEngine(llm_service)
    try:
        await engine.dismiss_question(db, question_id, current_user.id)
        return {"status": "ok", "message": "Clarification question dismissed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clarifications/{question_id}/approve")
async def approve_project_clarification(
    question_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from models.models import ClarificationQuestion, Fact, ActivityEvent
    async with db.begin_nested():
        stmt = select(ClarificationQuestion).where(ClarificationQuestion.id == question_id)
        res = await db.execute(stmt)
        q_record = res.scalar_one_or_none()
        if not q_record:
            raise HTTPException(status_code=404, detail="Clarification question not found")
        
        q_record.status = "resolved"
        q_record.resolved_by = current_user.id
        q_record.updated_at = datetime.now(timezone.utc)
        
        # Verify fact if linked
        if q_record.fact_id:
            fact_stmt = select(Fact).where(Fact.id == q_record.fact_id)
            fact = (await db.execute(fact_stmt)).scalar_one_or_none()
            if fact:
                if q_record.answer:
                    fact.object_text = q_record.answer
                fact.status = "verified"
                
        event = ActivityEvent(
            user_id=current_user.id,
            project_id=q_record.project_id,
            action_name="CLARIFICATION_QUESTION_APPROVED",
            payload={
                "question_id": str(question_id),
                "approved_by_user_id": str(current_user.id),
                "fact_id": str(q_record.fact_id) if q_record.fact_id else None
            }
        )
        db.add(event)
    await db.commit()
    return {"status": "ok", "message": "Clarification question approved successfully"}

from fastapi.responses import StreamingResponse
import json

class DocumentChatRequest(BaseModel):
    question: str
    selected_documents: Optional[List[uuid.UUID]] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    stream: bool = False
    mode: Optional[str] = "detailed"

@router.post("/{project_id}/conversations")
async def create_project_conversation(
    project_id: uuid.UUID,
    title: str = Query(...),
    selected_document_ids: Optional[List[str]] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Creates a new conversation in a project."""
    from services.conversation_engine import ConversationEngine
    conv = await ConversationEngine.create_conversation(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
        title=title,
        selected_document_ids=selected_document_ids
    )
    return {
        "conversation_id": str(conv.id),
        "title": conv.title,
        "status": conv.status,
        "selected_document_ids": conv.selected_document_ids
    }

@router.put("/{project_id}/conversations/{conversation_id}")
async def rename_project_conversation(
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    title: Optional[str] = Body(None),
    selected_document_ids: Optional[List[str]] = Body(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Updates (renames/pins docs) a conversation."""
    from services.conversation_engine import ConversationEngine
    conv = await ConversationEngine.update_conversation(
        db, conversation_id, title=title, selected_document_ids=selected_document_ids
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        "conversation_id": str(conv.id),
        "title": conv.title,
        "selected_document_ids": conv.selected_document_ids,
        "status": conv.status
    }

@router.post("/{project_id}/conversations/{conversation_id}/duplicate")
async def duplicate_project_conversation(
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Duplicates a conversation and its messages."""
    from services.conversation_engine import ConversationEngine
    conv = await ConversationEngine.get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    copy_title = f"Copy of {conv.title}"
    new_conv = await ConversationEngine.create_conversation(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
        title=copy_title,
        selected_document_ids=conv.selected_document_ids
    )
    
    history = await ConversationEngine.get_message_history(db, conversation_id, limit=200)
    for m in history:
        from models.models import Message
        msg = Message(
            id=uuid.uuid4(),
            conversation_id=new_conv.id,
            role=m.role,
            content=m.content,
            citations=m.citations or [],
            message_metadata=m.message_metadata or {}
        )
        db.add(msg)
    
    await db.commit()
    return {
        "conversation_id": str(new_conv.id),
        "title": new_conv.title,
        "status": new_conv.status,
        "selected_document_ids": new_conv.selected_document_ids
    }

@router.get("/{project_id}/conversations")
async def list_project_conversations(
    project_id: uuid.UUID,
    include_archived: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lists conversations in a project."""
    from services.conversation_engine import ConversationEngine
    conversations = await ConversationEngine.list_conversations(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
        include_archived=include_archived
    )
    return [
        {
            "conversation_id": str(c.id),
            "title": c.title,
            "status": c.status,
            "summary": c.summary,
            "selected_document_ids": c.selected_document_ids,
            "created_at": c.created_at,
            "updated_at": c.updated_at
        } for c in conversations
    ]

@router.delete("/{project_id}/conversations/{conversation_id}")
async def delete_project_conversation(
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deletes (soft-delete) a conversation."""
    from services.conversation_engine import ConversationEngine
    success = await ConversationEngine.delete_conversation(db, conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "ok", "message": "Conversation deleted successfully"}

@router.post("/{project_id}/conversations/{conversation_id}/archive")
async def archive_project_conversation(
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Archives a conversation."""
    from services.conversation_engine import ConversationEngine
    success = await ConversationEngine.archive_conversation(db, conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "ok", "message": "Conversation archived successfully"}

@router.post("/{project_id}/conversations/{conversation_id}/restore")
async def restore_project_conversation(
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Restores an archived or deleted conversation."""
    from services.conversation_engine import ConversationEngine
    success = await ConversationEngine.restore_conversation(db, conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "ok", "message": "Conversation restored successfully"}

@router.post("/{project_id}/conversations/{conversation_id}/chat")
async def document_chat(
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    request: DocumentChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Executes Document Chat API combining Context Retrieval, Prompt Building,
    and resilient LLM execution with citation payload structures and streaming.
    """
    from services.conversation_engine import ConversationEngine
    from services.retrieval_engine import RetrievalEngine
    from services.prompt_builder import PromptBuilder
    from services.llm_orchestrator import LLMOrchestrator
    from domain.value_objects.llm import LLMSettings

    # 1. Fetch conversation context
    conv = await ConversationEngine.get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Selected document constraints
    doc_uuids = None
    if request.selected_documents is not None:
        doc_uuids = request.selected_documents
    elif conv.selected_document_ids:
        doc_uuids = [uuid.UUID(d) for d in conv.selected_document_ids]

    filters = {}
    if request.page_start is not None:
        filters["page_start"] = request.page_start
    if request.page_end is not None:
        filters["page_end"] = request.page_end

    settings = LLMSettings(project_id=project_id, user_id=current_user.id, temperature=0.1)

    if request.stream:
        async def stream_generator():
            yield json.dumps({"stage": "retrieval_started"}) + "\n"
            
            # Fetch history
            history = await ConversationEngine.get_message_history(db, conversation_id, limit=50)
            history_list = [{"role": m.role, "content": m.content} for m in history]
            
            yield json.dumps({"stage": "searching"}) + "\n"
            
            # 2. Retrieve contexts
            retrieved_context = await RetrievalEngine.retrieve_context(
                db=db,
                project_id=project_id,
                query=request.question,
                conversation=history_list,
                selected_documents=doc_uuids,
                filters=filters,
                top_k=5,
                threshold=0.0
            )

            # Format citations metadata list
            citations = []
            for idx, chunk_text in enumerate(retrieved_context.retrieved_chunks):
                page_num = retrieved_context.pages[idx] if idx < len(retrieved_context.pages) else 1
                heading_text = retrieved_context.headings[idx] if idx < len(retrieved_context.headings) else None
                bbox = retrieved_context.bounding_boxes[idx] if idx < len(retrieved_context.bounding_boxes) else None
                doc_name = retrieved_context.document_names[idx] if idx < len(retrieved_context.document_names) else "Document"
                doc_id = retrieved_context.document_ids[idx] if idx < len(retrieved_context.document_ids) else None
                citations.append({
                    "page_number": page_num,
                    "heading": heading_text,
                    "bounding_box": bbox,
                    "document_name": doc_name,
                    "document_id": doc_id,
                    "snippet": chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text
                })

            yield json.dumps({"stage": "citations_found", "citations": citations}) + "\n"

            # 3. Compile structured PromptPackage
            prompt_package = PromptBuilder.build_package(
                retrieved_context=retrieved_context,
                conversation_summary=conv.summary,
                question=request.question,
                mode=request.mode or "detailed"
            )

            # Save user message to database history
            await ConversationEngine.add_message(db, conversation_id, "user", request.question)

            # If first message, auto-generate conversation title from the first question
            if len(history) == 0:
                words = request.question.split()
                auto_title = " ".join(words[:6])
                if len(words) > 6:
                    auto_title += "..."
                await ConversationEngine.update_conversation(db, conversation_id, title=auto_title)

            full_answer = []
            try:
                # Obtain async generator from LLMOrchestrator
                gen = await LLMOrchestrator.stream_execute(
                    logical_model_name="reasoning-heavy",
                    prompt_package=prompt_package,
                    settings=settings
                )
                async for chunk in gen:
                    full_answer.append(chunk.content)
                    yield json.dumps({"token": chunk.content}) + "\n"
            except Exception as e:
                logger.error(f"Streaming failed: {str(e)}")
                yield json.dumps({"error": str(e)}) + "\n"
                
            # Commit the completed message turn to database history
            completed_text = "".join(full_answer)
            await ConversationEngine.add_message(db, conversation_id, "assistant", completed_text, citations)
            await ConversationEngine.compress_history(db, conversation_id)
            
            yield json.dumps({"stage": "completed"}) + "\n"
            yield json.dumps({"done": True}) + "\n"

        return StreamingResponse(stream_generator(), media_type="application/x-ndjson")

    else:
        # Fetch history
        history = await ConversationEngine.get_message_history(db, conversation_id, limit=50)
        history_list = [{"role": m.role, "content": m.content} for m in history]

        # 2. Retrieve contexts
        retrieved_context = await RetrievalEngine.retrieve_context(
            db=db,
            project_id=project_id,
            query=request.question,
            conversation=history_list,
            selected_documents=doc_uuids,
            filters=filters,
            top_k=5,
            threshold=0.0
        )

        # 3. Compile structured PromptPackage
        prompt_package = PromptBuilder.build_package(
            retrieved_context=retrieved_context,
            conversation_summary=conv.summary,
            question=request.question,
            mode=request.mode or "detailed"
        )

        # Save user message to database history
        await ConversationEngine.add_message(db, conversation_id, "user", request.question)

        # If first message, auto-generate conversation title from the first question
        if len(history) == 0:
            words = request.question.split()
            auto_title = " ".join(words[:6])
            if len(words) > 6:
                auto_title += "..."
            await ConversationEngine.update_conversation(db, conversation_id, title=auto_title)

        # Format citations metadata list
        citations = []
        for idx, chunk_text in enumerate(retrieved_context.retrieved_chunks):
            page_num = retrieved_context.pages[idx] if idx < len(retrieved_context.pages) else 1
            heading_text = retrieved_context.headings[idx] if idx < len(retrieved_context.headings) else None
            bbox = retrieved_context.bounding_boxes[idx] if idx < len(retrieved_context.bounding_boxes) else None
            doc_name = retrieved_context.document_names[idx] if idx < len(retrieved_context.document_names) else "Document"
            doc_id = retrieved_context.document_ids[idx] if idx < len(retrieved_context.document_ids) else None
            citations.append({
                "page_number": page_num,
                "heading": heading_text,
                "bounding_box": bbox,
                "document_name": doc_name,
                "document_id": doc_id,
                "snippet": chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text
            })

        # Static invocation
        res = await LLMOrchestrator.execute(
            db=db,
            logical_model_name="reasoning-heavy",
            prompt_package=prompt_package,
            settings=settings
        )

        # Commit response to database history
        await ConversationEngine.add_message(db, conversation_id, "assistant", res.answer, citations)
        await ConversationEngine.compress_history(db, conversation_id)

        return {
            "answer": res.answer,
            "citations": citations,
            "latency_metrics": res.latency_ms,
            "token_usage": res.usage,
            "model": res.model,
            "provider": res.provider
        }

