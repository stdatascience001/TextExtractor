import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from sqlalchemy import select

from database.database import SessionLocal
from infrastructure.persistence.repositories.uow import SQLAlchemyUnitOfWork
from models.models import OutboxMessage, Fact, ConflictReport, ActivityEvent, KnowledgeEntity
from services.conflict_service import KnowledgeConflictDetector, RuleBasedConflictFilter
from services.llm_service import ResilientLLMService

logger = logging.getLogger("outbox_worker")

class OutboxWorker:
    def __init__(self, interval_seconds: float = 3.0):
        self.interval_seconds = interval_seconds
        self._running = False
        self._task = None

    def start(self):
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Outbox Background Worker started.")

    async def stop(self):
        self._running = False
        if self._task:
            try:
                self._task.cancel()
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Outbox Background Worker stopped.")

    async def _run_loop(self):
        while self._running:
            try:
                await self.process_pending_messages()
            except Exception as e:
                logger.error(f"Error in outbox worker loop: {str(e)}")
            await asyncio.sleep(self.interval_seconds)

    async def process_pending_messages(self):
        # Poll pending messages
        async with SessionLocal() as session:
            uow = SQLAlchemyUnitOfWork(session)
            pending_msgs = await uow.outbox.get_pending(limit=20)
            if not pending_msgs:
                return

            for msg in pending_msgs:
                try:
                    # Update status to processing
                    msg.status = "processing"
                    await uow.flush()
                    await uow.commit() # Save processing status immediately to avoid duplicate pickups!
                    
                    # Start processing the message in its own transaction block
                    async with session.begin_nested():
                        if msg.event_type == "FactCreated":
                            await self._handle_fact_created(uow, msg.payload)
                            
                        msg.status = "completed"
                        msg.processed_at = datetime.now(timezone.utc)
                    
                    await uow.commit()
                    logger.info(f"Processed outbox message {msg.id} successfully.")
                except Exception as e:
                    logger.error(f"Error processing outbox message {msg.id}: {str(e)}")
                    await uow.rollback()
                    
                    # Increment retry count or mark dead_letter
                    msg.retry_count += 1
                    msg.error_message = str(e)
                    if msg.retry_count >= msg.max_retries:
                        msg.status = "dead_letter"
                    else:
                        msg.status = "pending"
                    
                    await uow.commit()

    async def _handle_fact_created(self, uow: SQLAlchemyUnitOfWork, payload: dict):
        fact_id = uuid.UUID(payload["fact_id"])
        project_id = uuid.UUID(payload["project_id"])
        user_id = uuid.UUID(payload["user_id"])

        fact = await uow.facts.get_by_id(fact_id)
        if not fact:
            logger.warning(f"Fact {fact_id} not found, skipping outbox event.")
            return

        # Retrieve active sibling facts for the subject
        siblings = await uow.facts.get_active_siblings(project_id, fact.subject_id, fact.id)
        if not siblings:
            return

        # Initialize LLM detector (using ResilientLLMService)
        llm_service = ResilientLLMService()
        detector = KnowledgeConflictDetector(llm_service)

        for sibling in siblings:
            # Check for idempotency: does an active conflict report already exist for this pair?
            exists = await uow.conflicts.check_exists(fact.id, sibling.id, "duplicate") or \
                     await uow.conflicts.check_exists(fact.id, sibling.id, "numeric") or \
                     await uow.conflicts.check_exists(fact.id, sibling.id, "temporal") or \
                     await uow.conflicts.check_exists(fact.id, sibling.id, "different_value") or \
                     await uow.conflicts.check_exists(fact.id, sibling.id, "contradiction")
            if exists:
                continue

            # Evaluate heuristics first
            is_conflict, conflict_type = RuleBasedConflictFilter.evaluate_heuristic_match(
                fact.object_text, sibling.object_text
            )
            reasoning = ""
            recommended_resolution = ""

            if is_conflict:
                if conflict_type == "duplicate":
                    reasoning = f"Deterministic duplicate fact: '{fact.predicate}: {fact.object_text}'."
                    recommended_resolution = "Merge duplicate assertions."
                elif conflict_type == "numeric":
                    reasoning = f"Numeric mismatch: '{fact.predicate}' values differ between '{fact.object_text}' and '{sibling.object_text}'."
                    recommended_resolution = "Verify dosage/measurement units and values."
                elif conflict_type == "temporal":
                    reasoning = f"Temporal mismatch: onset/date year mismatch between '{fact.object_text}' and '{sibling.object_text}'."
                    recommended_resolution = "Check temporal timeline records."
            else:
                # Fallback to LLM call
                stmt_entity = select(KnowledgeEntity).where(KnowledgeEntity.id == fact.subject_id)
                entity_res = await uow.session.execute(stmt_entity)
                entity = entity_res.scalar_one_or_none()
                subject_name = entity.name if entity else "Unknown Entity"

                is_conflict, conflict_type, reasoning, recommended_resolution = await detector._evaluate_single_conflict_with_llm(
                    db=uow.session,
                    subject_name=subject_name,
                    predicate_a=fact.predicate,
                    object_a=fact.object_text,
                    conf_a=fact.confidence,
                    predicate_b=sibling.predicate,
                    object_b=sibling.object_text,
                    conf_b=sibling.confidence,
                    project_id=project_id,
                    user_id=user_id
                )

            if is_conflict and conflict_type != "none":
                logger.warning(f"Conflict of type '{conflict_type}' detected between fact {fact.id} and {sibling.id}: {reasoning}")
                
                # Lock statuses: Transition both to conflicted lifecycle state
                fact.status = "conflicted"
                sibling.status = "conflicted"

                # Create Conflict Report
                report = ConflictReport(
                    project_id=project_id,
                    first_fact_id=sibling.id,
                    second_fact_id=fact.id,
                    status="open",
                    conflict_type=conflict_type,
                    confidence_score=0.95 if conflict_type == "duplicate" else (fact.confidence + sibling.confidence) / 2.0,
                    llm_model="groq/llama3",
                    reasoning=reasoning,
                    resolution_notes=f"Heuristic/AI match: {reasoning}\nRecommendation: {recommended_resolution}"
                )
                await uow.conflicts.save(report)
                await uow.flush() # Populate ID

                # Log audit event: CONFLICT_CREATED
                event = ActivityEvent(
                    user_id=user_id,
                    project_id=project_id,
                    action_name="CONFLICT_CREATED",
                    payload={
                        "conflict_report_id": str(report.id),
                        "first_fact_id": str(sibling.id),
                        "second_fact_id": str(fact.id),
                        "conflict_type": conflict_type,
                        "reasoning": reasoning
                    }
                )
                uow.add(event)

# Global singleton worker instance
worker_instance = OutboxWorker()
