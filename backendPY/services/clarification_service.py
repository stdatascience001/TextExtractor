import uuid
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Type
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from domain.value_objects.llm import LLMSettings
from models.models import ClarificationQuestion, ConflictReport, Fact, ActivityEvent, KnowledgeEntity
from services.llm_service import ResilientLLMService, PromptRegistry

logger = logging.getLogger("clarification_service")

class ClarificationQuestionSchema(BaseModel):
    question: str = Field(description="The clear question text to ask the human reviewer.")
    reason: str = Field(description="The reason why this question was triggered (e.g. low confidence, conflict, missing data).")
    evidence: str = Field(description="Verbatim text snippets or context details surrounding the ambiguity.")
    priority: str = Field(description="Priority level: high, medium, or low.")
    suggested_answer_type: str = Field(description="The UI answer component type: boolean, choice, or text.")
    choices: Optional[List[str]] = Field(default=None, description="If type is choice, provide list of options.")

class KnowledgeClarificationEngine:
    def __init__(self, llm_service: ResilientLLMService):
        self.llm_service = llm_service

    async def generate_clarification_question(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        document_id: Optional[uuid.UUID],
        reason: str,
        evidence: str,
        trigger_type: str,
        fact_id: Optional[uuid.UUID] = None,
        entity_id: Optional[uuid.UUID] = None,
        priority: str = "medium"
    ) -> uuid.UUID:
        """Invokes LLM reasoning, validates schemas, serializes question text payloads, and saves to PostgreSQL."""
        logger.info(f"Generating clarification question for project {project_id} (Reason: {reason})")

        variables = {
            "reason": reason,
            "evidence": evidence,
            "priority": priority,
        }

        try:
            prompt = await PromptRegistry.get_prompt(db, "clarification_generation", variables)
        except Exception:
            sys_prompt = "You are a professional clinical clarification question generator. You formulate questions to resolve data ambiguity."
            user_prompt = (
                f"Formulate a structured clarification question for the reviewer based on:\n"
                f"Reason: {reason}\n"
                f"Evidence: {evidence}\n"
                f"Priority: {priority}\n\n"
                f"Output JSON matching the schema:\n"
                f"{json.dumps(ClarificationQuestionSchema.model_json_schema())}"
            )
            prompt = f"System Prompt:\n{sys_prompt}\n\nUser Message:\n{user_prompt}"

        settings = LLMSettings(
            temperature=0.2,
            json_mode=True,
            project_id=project_id,
            user_id=user_id
        )

        response = await self.llm_service.generate("reasoning-heavy", prompt, settings)
        q_schema = ClarificationQuestionSchema.model_validate_json(response.content)

        # Persistence: Serialize JSON schema to 'question' column
        async with db.begin_nested():
            q_record = ClarificationQuestion(
                project_id=project_id,
                document_id=document_id,
                question=q_schema.model_dump_json(),
                status="open",
                trigger_type=trigger_type,
                fact_id=fact_id,
                entity_id=entity_id
            )
            db.add(q_record)
            await db.flush() # Populate ID

            # Log audit CLARIFICATION_QUESTION_GENERATED event
            event = ActivityEvent(
                user_id=user_id,
                project_id=project_id,
                action_name="CLARIFICATION_QUESTION_GENERATED",
                payload={
                    "question_id": str(q_record.id),
                    "reason": reason,
                    "trigger_type": trigger_type,
                    "fact_id": str(fact_id) if fact_id else None,
                    "entity_id": str(entity_id) if entity_id else None,
                    "priority": priority
                }
            )
            db.add(event)

        await db.commit()
        logger.info(f"Clarification question {q_record.id} persisted successfully.")
        return q_record.id

    async def resolve_question(
        self,
        db: AsyncSession,
        question_id: uuid.UUID,
        answer: str,
        user_id: uuid.UUID
    ):
        """Resolves a question, populates the answer, and logs CLARIFICATION_QUESTION_ANSWERED."""
        logger.info(f"Resolving clarification question {question_id}")

        async with db.begin_nested():
            stmt = select(ClarificationQuestion).where(ClarificationQuestion.id == question_id)
            res = await db.execute(stmt)
            q_record = res.scalar_one_or_none()
            
            if not q_record:
                raise ValueError(f"Clarification question {question_id} not found.")

            # Update details
            q_record.answer = answer
            q_record.status = "answered"
            q_record.resolved_by = user_id
            q_record.updated_at = datetime.now(timezone.utc)

            # Log audit event
            event = ActivityEvent(
                user_id=user_id,
                project_id=q_record.project_id,
                action_name="CLARIFICATION_QUESTION_ANSWERED",
                payload={
                    "question_id": str(question_id),
                    "resolved_by_user_id": str(user_id),
                    "status": "answered"
                }
            )
            db.add(event)

        await db.commit()
        logger.info(f"Clarification question {question_id} answered successfully.")

    async def dismiss_question(
        self,
        db: AsyncSession,
        question_id: uuid.UUID,
        user_id: uuid.UUID
    ):
        """Dismisses a clarification question and logs CLARIFICATION_QUESTION_DISMISSED."""
        logger.info(f"Dismissing clarification question {question_id}")

        async with db.begin_nested():
            stmt = select(ClarificationQuestion).where(ClarificationQuestion.id == question_id)
            res = await db.execute(stmt)
            q_record = res.scalar_one_or_none()
            
            if not q_record:
                raise ValueError(f"Clarification question {question_id} not found.")

            # Update details
            q_record.status = "dismissed"
            q_record.resolved_by = user_id
            q_record.updated_at = datetime.now(timezone.utc)

            # Log audit event
            event = ActivityEvent(
                user_id=user_id,
                project_id=q_record.project_id,
                action_name="CLARIFICATION_QUESTION_DISMISSED",
                payload={
                    "question_id": str(question_id),
                    "resolved_by_user_id": str(user_id),
                    "status": "dismissed"
                }
            )
            db.add(event)

        await db.commit()
        logger.info(f"Clarification question {question_id} dismissed successfully.")

    async def check_and_trigger_clarifications(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        document_id: Optional[uuid.UUID] = None
    ) -> int:
        """Scans for active anomalies (low confidence, conflicts, missing values, missing entities) and triggers questions."""
        logger.info(f"Checking for clarification triggers in project: {project_id} (Doc: {document_id})")
        trigger_count = 0
        
        from models.models import Evidence, Chunk, Page

        # 1. Trigger: Missing Entity Check
        if document_id:
            stmt_entities = (
                select(KnowledgeEntity)
                .join(Fact, Fact.subject_id == KnowledgeEntity.id)
                .join(Evidence, Evidence.fact_id == Fact.id)
                .join(Chunk, Evidence.chunk_id == Chunk.id)
                .join(Page, Chunk.page_id == Page.id)
                .where(
                    and_(
                        Page.document_id == document_id,
                        or_(
                            KnowledgeEntity.entity_type == "unknown",
                            KnowledgeEntity.entity_type.is_(None),
                            KnowledgeEntity.name.ilike("%unknown%")
                        )
                    )
                )
            )
        else:
            stmt_entities = select(KnowledgeEntity).where(
                and_(
                    KnowledgeEntity.project_id == project_id,
                    or_(
                        KnowledgeEntity.entity_type == "unknown",
                        KnowledgeEntity.entity_type.is_(None),
                        KnowledgeEntity.name.ilike("%unknown%")
                    )
                )
            )
        res_entities = await db.execute(stmt_entities)
        unresolved_entities = res_entities.scalars().all()
        for ent in unresolved_entities:
            stmt_check = select(ClarificationQuestion).where(
                and_(
                    ClarificationQuestion.project_id == project_id,
                    ClarificationQuestion.entity_id == ent.id,
                    ClarificationQuestion.trigger_type == "missing_entity",
                    ClarificationQuestion.status == "open"
                )
            )
            if (await db.execute(stmt_check)).scalar_one_or_none():
                continue

            reason = "Subject entity type is unknown or unresolved"
            evidence = f"Entity '{ent.name}' is registered without a confirmed clinical classification type (Entity ID: {ent.id})."
            await self.generate_clarification_question(
                db=db,
                project_id=project_id,
                user_id=user_id,
                document_id=document_id,
                reason=reason,
                evidence=evidence,
                trigger_type="missing_entity",
                entity_id=ent.id,
                priority="medium"
            )
            trigger_count += 1

        # 2. Trigger: Low Confidence Claims and Missing Values
        if document_id:
            subq = select(Evidence.fact_id).join(Chunk, Evidence.chunk_id == Chunk.id).join(Page, Chunk.page_id == Page.id).where(Page.document_id == document_id)
            stmt_facts = select(Fact).where(
                and_(
                    Fact.project_id == project_id,
                    Fact.id.in_(subq),
                    Fact.deleted_at.is_(None)
                )
            )
        else:
            stmt_facts = select(Fact).where(
                and_(
                    Fact.project_id == project_id,
                    Fact.deleted_at.is_(None)
                )
            )
        res_facts = await db.execute(stmt_facts)
        all_facts = res_facts.scalars().all()

        for fact in all_facts:
            # Low Confidence (< 0.75)
            if fact.confidence < 0.75:
                stmt_check = select(ClarificationQuestion).where(
                    and_(
                        ClarificationQuestion.project_id == project_id,
                        ClarificationQuestion.fact_id == fact.id,
                        ClarificationQuestion.trigger_type == "low_confidence",
                        ClarificationQuestion.status == "open"
                    )
                )
                if not (await db.execute(stmt_check)).scalar_one_or_none():
                    reason = f"Low confidence claim extraction (Confidence: {fact.confidence})"
                    evidence = f"Fact triple extracted: {fact.predicate} with value '{fact.object_text}' (Fact ID: {fact.id})."
                    await self.generate_clarification_question(
                        db=db,
                        project_id=project_id,
                        user_id=user_id,
                        document_id=document_id,
                        reason=reason,
                        evidence=evidence,
                        trigger_type="low_confidence",
                        fact_id=fact.id,
                        entity_id=fact.subject_id,
                        priority="low"
                    )
                    trigger_count += 1

            # Missing Value
            val_clean = (fact.object_text or "").strip().lower()
            if not val_clean or val_clean in ["n/a", "unknown", "none", "nil", "null", "undefined"]:
                stmt_check = select(ClarificationQuestion).where(
                    and_(
                        ClarificationQuestion.project_id == project_id,
                        ClarificationQuestion.fact_id == fact.id,
                        ClarificationQuestion.trigger_type == "missing_value",
                        ClarificationQuestion.status == "open"
                    )
                )
                if not (await db.execute(stmt_check)).scalar_one_or_none():
                    reason = f"Missing value assertion for predicate '{fact.predicate}'"
                    evidence = f"Claim registers an empty or placeholder value '{fact.object_text}' for subject entity {fact.subject_id}."
                    await self.generate_clarification_question(
                        db=db,
                        project_id=project_id,
                        user_id=user_id,
                        document_id=document_id,
                        reason=reason,
                        evidence=evidence,
                        trigger_type="missing_value",
                        fact_id=fact.id,
                        entity_id=fact.subject_id,
                        priority="medium"
                    )
                    trigger_count += 1

        # 3. Trigger: Active Contradiction Conflicts
        if document_id:
            fact_subq = select(Evidence.fact_id).join(Chunk, Evidence.chunk_id == Chunk.id).join(Page, Chunk.page_id == Page.id).where(Page.document_id == document_id)
            stmt_conflicts = select(ConflictReport).where(
                and_(
                    ConflictReport.project_id == project_id,
                    ConflictReport.status.in_(["active", "open"]),
                    or_(
                        ConflictReport.first_fact_id.in_(fact_subq),
                        ConflictReport.second_fact_id.in_(fact_subq)
                    )
                )
            )
        else:
            stmt_conflicts = select(ConflictReport).where(
                and_(
                    ConflictReport.project_id == project_id,
                    ConflictReport.status.in_(["active", "open"])
                )
            )
            
        res_conflicts = await db.execute(stmt_conflicts)
        active_conflicts = res_conflicts.scalars().all()

        for conflict in active_conflicts:
            stmt_check = select(ClarificationQuestion).where(
                and_(
                    ClarificationQuestion.project_id == project_id,
                    ClarificationQuestion.fact_id == conflict.second_fact_id,
                    ClarificationQuestion.trigger_type == "conflict",
                    ClarificationQuestion.status == "open"
                )
            )
            q_res = await db.execute(stmt_check)
            if q_res.scalar_one_or_none():
                continue

            reason = f"Active claim contradiction conflict detected ({conflict.conflict_type})"
            evidence = f"Clashing statements between: '{conflict.resolution_notes}' (Conflict ID: {conflict.id})."
            
            await self.generate_clarification_question(
                db=db,
                project_id=project_id,
                user_id=user_id,
                document_id=document_id,
                reason=reason,
                evidence=evidence,
                trigger_type="conflict",
                fact_id=conflict.second_fact_id,
                priority="high"
            )
            trigger_count += 1

        return trigger_count
