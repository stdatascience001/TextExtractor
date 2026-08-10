import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from models.models import Fact, ActivityEvent

logger = logging.getLogger("review_service")

class KnowledgeReviewService:
    @classmethod
    async def approve_fact(cls, db: AsyncSession, fact_id: uuid.UUID, user_id: uuid.UUID) -> Fact:
        """Approves a fact, changing its status to verified and confidence to 1.0."""
        logger.info(f"User {user_id} approving fact {fact_id}")

        async with db.begin_nested():
            stmt = select(Fact).where(Fact.id == fact_id)
            res = await db.execute(stmt)
            fact = res.scalar_one_or_none()
            if not fact:
                raise ValueError(f"Fact {fact_id} not found.")

            # Prior state details
            prior_status = fact.status
            prior_conf = fact.confidence

            # Transitions
            fact.status = "verified"
            fact.confidence = 1.0
            fact.updated_at = datetime.now(timezone.utc)

            # Audit
            event = ActivityEvent(
                user_id=user_id,
                project_id=fact.project_id,
                action_name="FACT_APPROVED",
                payload={
                    "fact_id": str(fact_id),
                    "prior_state": {
                        "status": prior_status,
                        "confidence": prior_conf
                    }
                }
            )
            db.add(event)

        await cls.sync_fact_to_search_index(db, fact_id)
        await db.commit()
        return fact

    @classmethod
    async def reject_fact(cls, db: AsyncSession, fact_id: uuid.UUID, user_id: uuid.UUID) -> Fact:
        """Rejects a fact, soft-deleting it and locking it from searches."""
        logger.info(f"User {user_id} rejecting fact {fact_id}")

        async with db.begin_nested():
            stmt = select(Fact).where(Fact.id == fact_id)
            res = await db.execute(stmt)
            fact = res.scalar_one_or_none()
            if not fact:
                raise ValueError(f"Fact {fact_id} not found.")

            # Prior state
            prior_status = fact.status
            prior_del = fact.deleted_at

            # Transitions
            fact.status = "rejected"
            fact.deleted_at = datetime.now(timezone.utc)
            fact.updated_at = datetime.now(timezone.utc)

            # Audit
            event = ActivityEvent(
                user_id=user_id,
                project_id=fact.project_id,
                action_name="FACT_REJECTED",
                payload={
                    "fact_id": str(fact_id),
                    "prior_state": {
                        "status": prior_status,
                        "deleted_at": prior_del.isoformat() if prior_del else None
                    }
                }
            )
            db.add(event)

        await cls.sync_fact_to_search_index(db, fact_id)
        await db.commit()
        return fact

    @classmethod
    async def modify_fact(
        cls,
        db: AsyncSession,
        fact_id: uuid.UUID,
        user_id: uuid.UUID,
        new_predicate: str,
        new_object_text: str
    ) -> Fact:
        """Modifies a fact, updating values, setting status to verified and recording the prior state version."""
        logger.info(f"User {user_id} modifying fact {fact_id}")

        async with db.begin_nested():
            stmt = select(Fact).where(Fact.id == fact_id)
            res = await db.execute(stmt)
            fact = res.scalar_one_or_none()
            if not fact:
                raise ValueError(f"Fact {fact_id} not found.")

            # Version history prior state snapshot
            prior_state = {
                "predicate": fact.predicate,
                "object_text": fact.object_text,
                "status": fact.status,
                "confidence": fact.confidence
            }

            # Transitions
            fact.predicate = new_predicate.strip()
            fact.object_text = new_object_text.strip()
            fact.status = "verified"
            fact.confidence = 1.0
            fact.updated_at = datetime.now(timezone.utc)

            # Audit modification event containing diff snapshots
            event = ActivityEvent(
                user_id=user_id,
                project_id=fact.project_id,
                action_name="FACT_MODIFIED",
                payload={
                    "fact_id": str(fact_id),
                    "prior_state": prior_state,
                    "new_state": {
                        "predicate": fact.predicate,
                        "object_text": fact.object_text,
                        "status": "verified",
                        "confidence": 1.0
                    }
                }
            )
            db.add(event)

            # Publish FactCreated event in outbox for asynchronous processing
            from services.outbox_service import OutboxService
            await OutboxService.publish_fact_created(db, fact.id, fact.project_id, user_id)

        await cls.sync_fact_to_search_index(db, fact_id)
        await db.commit()
        return fact

    @classmethod
    async def undo_last_action(cls, db: AsyncSession, fact_id: uuid.UUID, user_id: uuid.UUID) -> Fact:
        """Reverts the last verification action on a fact using the ActivityEvent audit registry."""
        logger.info(f"User {user_id} executing UNDO on last verification action for fact {fact_id}")

        async with db.begin_nested():
            # Query active fact record (include soft-deleted items to handle rejection reverts)
            stmt = select(Fact).where(Fact.id == fact_id)
            res = await db.execute(stmt)
            fact = res.scalar_one_or_none()
            if not fact:
                raise ValueError(f"Fact {fact_id} not found.")

            # Query the latest verification activity event logs for this fact_id
            stmt_event = (
                select(ActivityEvent)
                .where(
                    ActivityEvent.action_name.in_(["FACT_APPROVED", "FACT_REJECTED", "FACT_MODIFIED"]),
                )
                .order_by(ActivityEvent.created_at.desc())
            )
            res_event = await db.execute(stmt_event)
            events = res_event.scalars().all()
            
            target_event = None
            for ev in events:
                if ev.payload.get("fact_id") == str(fact_id):
                    target_event = ev
                    break

            if not target_event:
                raise ValueError(f"No reversible verification activity event logs found for fact {fact_id}")

            prior = target_event.payload["prior_state"]

            # Reversion transitions based on event action triggers
            if target_event.action_name == "FACT_APPROVED":
                fact.status = prior["status"]
                fact.confidence = prior["confidence"]
            elif target_event.action_name == "FACT_REJECTED":
                fact.status = prior["status"]
                fact.deleted_at = None # Revert soft delete!
            elif target_event.action_name == "FACT_MODIFIED":
                fact.predicate = prior["predicate"]
                fact.object_text = prior["object_text"]
                fact.status = prior["status"]
                fact.confidence = prior["confidence"]

            fact.updated_at = datetime.now(timezone.utc)

            # Remove target event to prevent duplicate undos
            await db.delete(target_event)

            # Log UNDONE confirmation audit
            undo_log = ActivityEvent(
                user_id=user_id,
                project_id=fact.project_id,
                action_name="FACT_ACTION_UNDONE",
                payload={
                    "fact_id": str(fact_id),
                    "undone_action_type": target_event.action_name
                }
            )
            db.add(undo_log)

        await cls.sync_fact_to_search_index(db, fact_id)
        await db.commit()
        return fact

    @classmethod
    async def sync_fact_to_search_index(cls, db: AsyncSession, fact_id: uuid.UUID):
        """Synchronizes fact changes to the searchable index chunk vectors."""
        from models.models import Fact, KnowledgeEntity, Chunk, Embedding, Page, Document
        from sqlalchemy.orm import selectinload
        from services.embedding_service import EmbeddingModelRegistry
        import os

        # Retrieve fact
        stmt = (
            select(Fact)
            .options(selectinload(Fact.subject), selectinload(Fact.evidence))
            .where(Fact.id == fact_id)
        )
        res = await db.execute(stmt)
        fact = res.scalar_one_or_none()
        
        if not fact:
            return

        pseudo_content_prefix = f"Fact ID: {fact.id} -"
        
        # If fact is deleted, rejected, or unverified: remove any indexed pseudo-chunk
        if fact.deleted_at is not None or fact.status != "verified":
            chunk_stmt = select(Chunk).where(Chunk.content.like(f"{pseudo_content_prefix}%"))
            chunk_res = await db.execute(chunk_stmt)
            chunks = chunk_res.scalars().all()
            for chk in chunks:
                await db.delete(chk)
            return

        # Build clean clinical fact context string
        fact_text = f"Fact ID: {fact.id} - {fact.subject.name} {fact.predicate} is {fact.object_text}"

        # Find or fallback page_id
        page_id = None
        if fact.evidence:
            ev_chunk_stmt = select(Chunk).where(Chunk.id == fact.evidence[0].chunk_id)
            ev_chunk_res = await db.execute(ev_chunk_stmt)
            ev_chunk = ev_chunk_res.scalar_one_or_none()
            if ev_chunk:
                page_id = ev_chunk.page_id
        
        if not page_id:
            page_stmt = select(Page).join(Document).where(Document.project_id == fact.project_id).limit(1)
            page_res = await db.execute(page_stmt)
            page_id = page_res.scalar()
            
        if not page_id:
            return

        # Fetch or insert pseudo-chunk
        chunk_stmt = select(Chunk).where(Chunk.content.like(f"{pseudo_content_prefix}%"))
        chunk_res = await db.execute(chunk_stmt)
        chunk = chunk_res.scalar_one_or_none()
        
        if not chunk:
            max_idx_stmt = select(Chunk.chunk_index).where(Chunk.page_id == page_id).order_by(Chunk.chunk_index.desc()).limit(1)
            max_idx_res = await db.execute(max_idx_stmt)
            max_idx = max_idx_res.scalar_one_or_none() or 0
            chunk = Chunk(
                id=uuid.uuid4(),
                page_id=page_id,
                chunk_index=max_idx + 1,
                content=fact_text
            )
            db.add(chunk)
            await db.flush()
        else:
            chunk.content = fact_text

        # Generate vectors
        active_model = os.getenv("ACTIVE_EMBEDDING_MODEL", "nomic-embed-text")
        adapter = EmbeddingModelRegistry.get_adapter(active_model)
        vectors = adapter.generate_embeddings([fact_text])
        vector = vectors[0]

        # Upsert embedding
        emb_stmt = select(Embedding).where(Embedding.chunk_id == chunk.id, Embedding.model_name == active_model)
        emb_res = await db.execute(emb_stmt)
        emb = emb_res.scalar_one_or_none()
        if not emb:
            emb = Embedding(
                id=uuid.uuid4(),
                chunk_id=chunk.id,
                embedding=vector,
                model_name=active_model
            )
            db.add(emb)
        else:
            emb.embedding = vector
