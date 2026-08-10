import uuid
import logging
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from models.models import KnowledgeEntity, Fact, Evidence, ActivityEvent

logger = logging.getLogger("knowledge_merger")

class KnowledgeMergeEngine:
    @staticmethod
    async def merge_duplicate_entities(
        db: AsyncSession,
        project_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> List[Tuple[uuid.UUID, uuid.UUID]]:
        """
        Scans, detects, and merges duplicate entities in a project.
        Returns a list of tuples representing (merged_entity_id, canonical_entity_id).
        """
        logger.info(f"Scanning for duplicate entities in project {project_id}")
        
        # Fetch all entities in the project
        stmt = select(KnowledgeEntity).where(
            KnowledgeEntity.project_id == project_id,
            KnowledgeEntity.deleted_at.is_(None)
        )
        res = await db.execute(stmt)
        entities = res.scalars().all()

        # Group by normalized key: lowercase name + lowercase type
        seen: dict = {}
        merges: List[Tuple[uuid.UUID, uuid.UUID]] = []

        for entity in entities:
            key = f"{entity.name.strip().lower()}_{entity.entity_type.strip().lower()}"
            if key in seen:
                canonical = seen[key]
                # Flag merge redirection
                merges.append((entity.id, canonical.id))
            else:
                seen[key] = entity

        if not merges:
            logger.info("No duplicate entities discovered.")
            return []

        # Process merges: Redirect subject_id references on facts to the canonical ID
        for duplicate_id, canonical_id in merges:
            logger.info(f"Merging entity {duplicate_id} into canonical entity {canonical_id}")
            
            # Update facts
            stmt_update = (
                update(Fact)
                .where(Fact.subject_id == duplicate_id)
                .values(subject_id=canonical_id)
            )
            await db.execute(stmt_update)

            # Soft delete the duplicate entity record
            stmt_delete = (
                update(KnowledgeEntity)
                .where(KnowledgeEntity.id == duplicate_id)
                .values(deleted_at=sa.func.now())
            )
            # Sa is not imported directly, we use DB func or import sa
            import sqlalchemy as sa
            stmt_delete = (
                update(KnowledgeEntity)
                .where(KnowledgeEntity.id == duplicate_id)
                .values(deleted_at=sa.func.now())
            )
            await db.execute(stmt_delete)

            # Log merge action
            event = ActivityEvent(
                user_id=user_id,
                project_id=project_id,
                action_name="ENTITY_MERGED",
                payload={
                    "duplicate_entity_id": str(duplicate_id),
                    "canonical_entity_id": str(canonical_id)
                }
            )
            db.add(event)

        try:
            await db.commit()
            logger.info(f"Successfully processed {len(merges)} entity merges.")
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to commit entity merges: {str(e)}")
            raise e

        return merges

    @staticmethod
    async def merge_duplicate_facts(
        db: AsyncSession,
        project_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> List[Tuple[uuid.UUID, uuid.UUID]]:
        """
        Scans, detects, and merges duplicate facts in a project.
        Re-calculates confidence using probabilistic sum and relocates evidence links.
        """
        logger.info(f"Scanning for duplicate facts in project {project_id}")

        stmt = select(Fact).where(
            Fact.project_id == project_id,
            Fact.deleted_at.is_(None)
        )
        res = await db.execute(stmt)
        facts = res.scalars().all()

        seen: dict = {}
        merges: List[Tuple[uuid.UUID, uuid.UUID]] = []

        for fact in facts:
            # Duplicate key: same subject_id, predicate, and normalized object value
            key = f"{fact.subject_id}_{fact.predicate.strip().lower()}_{fact.object_text.strip().lower()}"
            if key in seen:
                canonical = seen[key]
                merges.append((fact.id, canonical.id))
            else:
                seen[key] = fact

        if not merges:
            logger.info("No duplicate facts discovered.")
            return []

        import sqlalchemy as sa
        for duplicate_id, canonical_id in merges:
            logger.info(f"Merging fact {duplicate_id} into canonical fact {canonical_id}")

            # 1. Fetch values to re-calculate confidence
            stmt_dup = select(Fact).where(Fact.id == duplicate_id)
            stmt_can = select(Fact).where(Fact.id == canonical_id)
            
            dup_fact = (await db.execute(stmt_dup)).scalar_one()
            can_fact = (await db.execute(stmt_can)).scalar_one()

            # Probabilistic sum: C_merged = 1 - (1 - C_1) * (1 - C_2)
            c1 = can_fact.confidence
            c2 = dup_fact.confidence
            merged_confidence = round(1.0 - ((1.0 - c1) * (1.0 - c2)), 4)

            # Limit confidence to maximum 0.9999 to avoid floating point anomalies reaching 1.0
            merged_confidence = min(merged_confidence, 0.9999)

            # 2. Re-assign all Evidence linkages to canonical ID
            stmt_evidence = (
                update(Evidence)
                .where(Evidence.fact_id == duplicate_id)
                .values(fact_id=canonical_id)
            )
            await db.execute(stmt_evidence)

            # 3. Update canonical fact confidence
            can_fact.confidence = merged_confidence
            can_fact.updated_at = sa.func.now()

            # 4. Soft delete duplicate fact
            stmt_del = (
                update(Fact)
                .where(Fact.id == duplicate_id)
                .values(deleted_at=sa.func.now())
            )
            await db.execute(stmt_del)

            # Log merge details
            event = ActivityEvent(
                user_id=user_id,
                project_id=project_id,
                action_name="FACT_MERGED",
                payload={
                    "duplicate_fact_id": str(duplicate_id),
                    "canonical_fact_id": str(canonical_id),
                    "prior_confidence": c1,
                    "added_confidence": c2,
                    "merged_confidence": merged_confidence
                }
            )
            db.add(event)

        try:
            await db.commit()
            logger.info(f"Successfully processed {len(merges)} fact merges.")
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to commit fact merges: {str(e)}")
            raise e

        return merges
