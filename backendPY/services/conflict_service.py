import uuid
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from domain.value_objects.llm import LLMSettings
from models.models import KnowledgeEntity, Fact, ConflictReport, ActivityEvent
from services.llm_service import ResilientLLMService, PromptRegistry

logger = logging.getLogger("conflict_service")

import re

# 1. Pydantic schema for LLM reasoning
class ConflictEvaluationSchema(BaseModel):
    is_conflict: bool = Field(description="True if Statement A and Statement B are mutually exclusive, duplicate, or represent conflicting values/temporals/numerics.")
    conflict_type: str = Field(description="One of: 'contradiction', 'different_value', 'duplicate', 'temporal', 'numeric', or 'none'.")
    reasoning: str = Field(description="Detailed explanation of the semantic contradiction or value conflict.")
    recommended_resolution: str = Field(description="Suggested resolution based on clinical context or confidence scores.")

class RuleBasedConflictFilter:
    @staticmethod
    def normalize_text(text: str) -> str:
        """Strips punctuation, spacing, casing, and clinical units/stopwords."""
        text = text.lower().strip()
        text = re.sub(r'[^\w\s\.]', '', text) # preserve dots for decimals
        # Strip common clinical units/stopwords
        text = re.sub(r'\b(mg|mcg|g|tab|tabs|caps|capsule|capsules|daily|qd|bid|tid|qid|once)\b', '', text)
        return " ".join(text.split())

    @staticmethod
    def extract_numeric_value(text: str) -> Optional[float]:
        """Extracts first valid integer/float value from text."""
        match = re.search(r'\b\d+(?:\.\d+)?\b', text)
        try:
            return float(match.group(0)) if match else None
        except Exception:
            return None

    @classmethod
    def evaluate_heuristic_match(cls, val_a: str, val_b: str) -> Tuple[bool, str]:
        """
        Returns (is_conflict, conflict_type).
        If 'duplicate', the statements are duplicates/identical.
        If 'numeric', the numbers represent conflicting dosages or values.
        If 'needs_llm', requires semantic evaluation.
        """
        norm_a = cls.normalize_text(val_a)
        norm_b = cls.normalize_text(val_b)
        
        # Exact Normalized Match (Duplicate Fact)
        if norm_a == norm_b:
            return True, "duplicate"

        # Numeric Conflict Check
        num_a = cls.extract_numeric_value(val_a)
        num_b = cls.extract_numeric_value(val_b)
        if num_a is not None and num_b is not None:
            if num_a != num_b:
                return True, "numeric"

        # Check for simple date match clashing (e.g. 2021 vs 2023)
        year_match_a = re.search(r'\b(19|20)\d{2}\b', val_a)
        year_match_b = re.search(r'\b(19|20)\d{2}\b', val_b)
        if year_match_a and year_match_b:
            if year_match_a.group(0) != year_match_b.group(0):
                return True, "temporal"

        # If we cannot resolve it deterministically, return needs_llm
        return False, "needs_llm"

# 2. Conflict Detection Engine
class KnowledgeConflictDetector:
    def __init__(self, llm_service: ResilientLLMService):
        self.llm_service = llm_service

    async def detect_and_report_conflicts(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> int:
        """Compares fact pairs, triggers LLM reasoning evaluations, maps conflict reports, and locks claims."""
        logger.info(f"Initiating AI conflict detection engine for project: {project_id}")

        # A. Query active facts in project
        stmt = select(Fact).where(
            and_(
                Fact.project_id == project_id,
                Fact.deleted_at.is_(None)
            )
        )
        res = await db.execute(stmt)
        facts = res.scalars().all()

        # Group facts by: (subject_id, predicate.lower())
        groups: Dict[Tuple[uuid.UUID, str], List[Fact]] = {}
        for fact in facts:
            key = (fact.subject_id, fact.predicate.strip().lower())
            groups.setdefault(key, []).append(fact)

        conflict_count = 0

        # B. Pairwise comparison of facts sharing subject/predicate
        for key, fact_list in groups.items():
            if len(fact_list) <= 1:
                continue

            subject_id, predicate = key
            
            # Fetch Subject entity name
            subj_stmt = select(KnowledgeEntity.name).where(KnowledgeEntity.id == subject_id)
            subj_res = await db.execute(subj_stmt)
            subject_name = subj_res.scalar_one_or_none() or "Unknown Entity"

            for i in range(len(fact_list)):
                for j in range(i + 1, len(fact_list)):
                    fact_a = fact_list[i]
                    fact_b = fact_list[j]

                    # Skip if objects match exactly (handled by merge engine)
                    if fact_a.object_text.strip().lower() == fact_b.object_text.strip().lower():
                        continue

                    # Check if an active conflict report already exists for this pair
                    conflict_check = await db.execute(
                        select(ConflictReport).where(
                            and_(
                                ConflictReport.project_id == project_id,
                                ConflictReport.status.in_(["active", "open"]),
                                or_(
                                    and_(ConflictReport.first_fact_id == fact_a.id, ConflictReport.second_fact_id == fact_b.id),
                                    and_(ConflictReport.first_fact_id == fact_b.id, ConflictReport.second_fact_id == fact_a.id)
                                )
                            )
                        )
                    )
                    existing_report = conflict_check.scalar_one_or_none()
                    if existing_report:
                        continue

                    # Execute LLM semantic contradiction reasoning evaluation
                    is_conflict, reasoning = await self._evaluate_conflict_with_llm(
                        db=db,
                        subject_name=subject_name,
                        predicate=predicate,
                        fact_a=fact_a,
                        fact_b=fact_b,
                        project_id=project_id,
                        user_id=user_id
                    )

                    if is_conflict:
                        logger.info(f"Conflict detected between fact {fact_a.id} and {fact_b.id}: {reasoning}")
                        
                        # Lock facts (Status reset to unverified)
                        async with db.begin_nested():
                            fact_a.status = "unverified"
                            fact_b.status = "unverified"

                            # Create Conflict Report
                            report = ConflictReport(
                                project_id=project_id,
                                first_fact_id=fact_a.id,
                                second_fact_id=fact_b.id,
                                status="open",
                                resolution_notes=reasoning
                            )
                            db.add(report)
                            await db.flush() # Populate ID

                            # Log audit CONFLICT_DETECTED event
                            event = ActivityEvent(
                                user_id=user_id,
                                project_id=project_id,
                                action_name="CONFLICT_DETECTED",
                                payload={
                                    "conflict_report_id": str(report.id),
                                    "fact_a_id": str(fact_a.id),
                                    "fact_b_id": str(fact_b.id),
                                    "reasoning": reasoning
                                }
                            )
                            db.add(event)
                        
                        await db.commit()
                        conflict_count += 1

        return conflict_count

    async def _evaluate_conflict_with_llm(
        self,
        db: AsyncSession,
        subject_name: str,
        predicate: str,
        fact_a: Fact,
        fact_b: Fact,
        project_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Tuple[bool, str]:
        """Queries the reasoning-heavy model to determine if two statements are semantically exclusive."""
        variables = {
            "subject_name": subject_name,
            "predicate": predicate,
            "fact_a_value": fact_a.object_text,
            "fact_a_conf": fact_a.confidence,
            "fact_b_value": fact_b.object_text,
            "fact_b_conf": fact_b.confidence,
        }

        # Attempt to load custom templates from registry, falling back on fail
        try:
            prompt = await PromptRegistry.get_prompt(db, "conflict_reasoning", variables)
        except Exception:
            sys_prompt = (
                "You are an AI clinical logic validator. Analyze if two medical statements about the same subject conflict or contradict each other.\n"
                "Analyze the relationship and classify conflicts into one of these categories:\n"
                "- 'contradiction': Mutually exclusive statements (e.g. positive vs negative, active vs resolved, present vs absent).\n"
                "- 'different_value': Different values or outcomes for the same predicate (e.g., location is 'left lung' vs 'right lung').\n"
                "- 'duplicate': Identical or semantically equivalent statements (e.g., diagnosed with 'diabetes' vs 'type 2 diabetes mellitus').\n"
                "- 'temporal': Clashing timeline assertions or different onset dates (e.g., diagnosed in '2021' vs '2023').\n"
                "- 'numeric': Mismatched measurements, dosages, or numbers (e.g., dosage '500mg' vs '1000mg').\n"
                "- 'none': No conflict exists (statements are complementary)."
            )
            user_prompt = (
                f"Evaluate if these two claims are contradictory or mutually exclusive in a clinical report:\n"
                f"Subject: {subject_name}\n"
                f"Property/Predicate: {predicate}\n"
                f"Statement A: {fact_a.object_text} (Confidence: {fact_a.confidence})\n"
                f"Statement B: {fact_b.object_text} (Confidence: {fact_b.confidence})\n\n"
                f"Output a JSON object matching the schema:\n"
                f"{json.dumps(ConflictEvaluationSchema.model_json_schema())}"
            )
            prompt = f"System Prompt:\n{sys_prompt}\n\nUser Message:\n{user_prompt}"

        settings = LLMSettings(
            temperature=0.0,
            json_mode=True,
            project_id=project_id,
            user_id=user_id
        )

        try:
            response = await self.llm_service.generate("reasoning-heavy", prompt, settings)
            eval_schema = ConflictEvaluationSchema.model_validate_json(response.content)
            reasoning = f"Conflict Type: {eval_schema.conflict_type}\nReasoning: {eval_schema.reasoning}"
            if eval_schema.recommended_resolution:
                reasoning += f"\nRecommendation: {eval_schema.recommended_resolution}"
            return eval_schema.is_conflict, reasoning
        except Exception as e:
            logger.error(f"Error evaluating conflict reasoning via LLM: {str(e)}")
            # Default to false on runtime failure to prevent blocking the worker
            return False, ""

    async def check_conflicts_for_inserted_fact(
        self,
        db: AsyncSession,
        fact: Fact,
        user_id: uuid.UUID
    ) -> int:
        """
        Runs inline conflict check when a new fact is inserted or updated.
        Compares the new fact against existing active verified or unverified facts for the same subject.
        """
        logger.info(f"Inline conflict check triggered for fact {fact.id} (Subject: {fact.subject_id})")

        # 1. Fetch overlap candidate facts (same subject, excluding itself)
        stmt = select(Fact).where(
            and_(
                Fact.project_id == fact.project_id,
                Fact.subject_id == fact.subject_id,
                Fact.id != fact.id,
                Fact.deleted_at.is_(None),
                Fact.status.in_(["verified", "unverified"])
            )
        )
        res = await db.execute(stmt)
        candidates = res.scalars().all()

        if not candidates:
            return 0

        # Fetch subject entity details for prompt context
        stmt_entity = select(KnowledgeEntity).where(KnowledgeEntity.id == fact.subject_id)
        entity_res = await db.execute(stmt_entity)
        entity = entity_res.scalar_one_or_none()
        subject_name = entity.name if entity else "Unknown Entity"

        conflict_count = 0

        for candidate in candidates:
            # 2. Skip if an active conflict report already exists for this pair
            conflict_check = await db.execute(
                select(ConflictReport).where(
                    and_(
                        ConflictReport.project_id == fact.project_id,
                        ConflictReport.status.in_(["open", "active"]),
                        or_(
                            and_(ConflictReport.first_fact_id == fact.id, ConflictReport.second_fact_id == candidate.id),
                            and_(ConflictReport.first_fact_id == candidate.id, ConflictReport.second_fact_id == fact.id)
                        )
                    )
                )
            )
            existing_report = conflict_check.scalar_one_or_none()
            if existing_report:
                continue

            # 3. Detect and classify conflict using LLM & fast rules
            is_conflict = False
            conflict_type = "none"
            reasoning = ""
            recommended_resolution = ""

            # Exact duplicate check (fast path)
            if fact.predicate.strip().lower() == candidate.predicate.strip().lower() and \
               fact.object_text.strip().lower() == candidate.object_text.strip().lower():
                is_conflict = True
                conflict_type = "duplicate"
                reasoning = f"Duplicate facts detected for subject '{subject_name}' with predicate '{fact.predicate}'."
                recommended_resolution = "Merge duplicate facts into a single verified entry."
            else:
                # LLM check
                is_conflict, conflict_type, reasoning, recommended_resolution = await self._evaluate_single_conflict_with_llm(
                    db=db,
                    subject_name=subject_name,
                    predicate_a=fact.predicate,
                    object_a=fact.object_text,
                    conf_a=fact.confidence,
                    predicate_b=candidate.predicate,
                    object_b=candidate.object_text,
                    conf_b=candidate.confidence,
                    project_id=fact.project_id,
                    user_id=user_id
                )

            if is_conflict:
                logger.info(f"Conflict of type '{conflict_type}' detected between fact {fact.id} and {candidate.id}: {reasoning}")
                
                # Lock both facts (reset status to unverified)
                fact.status = "unverified"
                candidate.status = "unverified"

                # Create Conflict Report
                report = ConflictReport(
                    project_id=fact.project_id,
                    first_fact_id=candidate.id,
                    second_fact_id=fact.id,
                    status="open",
                    resolution_notes=f"Conflict Type: {conflict_type}\nReasoning: {reasoning}\nRecommendation: {recommended_resolution}"
                )
                db.add(report)
                await db.flush()

                # Log audit CONFLICT_DETECTED event
                event = ActivityEvent(
                    user_id=user_id,
                    project_id=fact.project_id,
                    action_name="CONFLICT_DETECTED",
                    payload={
                        "conflict_report_id": str(report.id),
                        "fact_a_id": str(candidate.id),
                        "fact_b_id": str(fact.id),
                        "conflict_type": conflict_type,
                        "reasoning": reasoning
                    }
                )
                db.add(event)
                conflict_count += 1

        return conflict_count

    async def _evaluate_single_conflict_with_llm(
        self,
        db: AsyncSession,
        subject_name: str,
        predicate_a: str,
        object_a: str,
        conf_a: float,
        predicate_b: str,
        object_b: str,
        conf_b: float,
        project_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Tuple[bool, str, str, str]:
        """Queries the reasoning-heavy model to determine if two statements are conflicting and classifies the type."""
        sys_prompt = (
            "You are an AI clinical logic validator. Analyze if two medical statements about the same subject conflict or contradict each other.\n"
            "Analyze the relationship and classify conflicts into one of these categories:\n"
            "- 'contradiction': Mutually exclusive statements (e.g. positive vs negative, active vs resolved, present vs absent).\n"
            "- 'different_value': Different values or outcomes for the same predicate (e.g., location is 'left lung' vs 'right lung').\n"
            "- 'duplicate': Identical or semantically equivalent statements (e.g., diagnosed with 'diabetes' vs 'type 2 diabetes mellitus').\n"
            "- 'temporal': Clashing timeline assertions or different onset dates (e.g., diagnosed in '2021' vs '2023').\n"
            "- 'numeric': Mismatched measurements, dosages, or numbers (e.g., dosage '500mg' vs '1000mg').\n"
            "- 'none': No conflict exists (statements are complementary)."
        )
        
        user_prompt = (
            f"Evaluate the conflict between these two claims:\n"
            f"Subject: {subject_name}\n"
            f"Statement A: Predicate/Relation: '{predicate_a}', Value: '{object_a}' (Confidence: {conf_a})\n"
            f"Statement B: Predicate/Relation: '{predicate_b}', Value: '{object_b}' (Confidence: {conf_b})\n\n"
            f"Output a JSON object matching this schema:\n"
            f"{json.dumps(ConflictEvaluationSchema.model_json_schema())}"
        )
        prompt = f"System Prompt:\n{sys_prompt}\n\nUser Message:\n{user_prompt}"

        settings = LLMSettings(
            temperature=0.0,
            json_mode=True,
            project_id=project_id,
            user_id=user_id
        )

        try:
            response = await self.llm_service.generate("reasoning-heavy", prompt, settings)
            eval_schema = ConflictEvaluationSchema.model_validate_json(response.content)
            return eval_schema.is_conflict, eval_schema.conflict_type, eval_schema.reasoning, eval_schema.recommended_resolution
        except Exception as e:
            logger.error(f"Error evaluating conflict reasoning via LLM: {str(e)}")
            return False, "none", "", ""

    async def resolve_conflict(
        self,
        db: AsyncSession,
        conflict_id: uuid.UUID,
        resolving_fact_id: uuid.UUID,
        user_id: uuid.UUID
    ):
        """Resolves a conflict report, locking status transitions and soft-deleting rejected claims."""
        logger.info(f"Resolving conflict report {conflict_id} using fact {resolving_fact_id}")

        async with db.begin_nested():
            # Query report
            stmt = select(ConflictReport).where(ConflictReport.id == conflict_id)
            res = await db.execute(stmt)
            report = res.scalar_one_or_none()
            if not report:
                raise ValueError(f"Conflict report {conflict_id} not found.")

            if report.status == "resolved":
                raise ValueError(f"Conflict report {conflict_id} has already been resolved.")

            # Retrieve conflicting facts
            fact_a_stmt = select(Fact).where(Fact.id == report.first_fact_id)
            fact_a_res = await db.execute(fact_a_stmt)
            fact_a = fact_a_res.scalar_one_or_none()

            fact_b_stmt = select(Fact).where(Fact.id == report.second_fact_id)
            fact_b_res = await db.execute(fact_b_stmt)
            fact_b = fact_b_res.scalar_one_or_none()

            if not fact_a or not fact_b:
                raise ValueError("Conflicting parent facts missing or deleted from database.")

            # Determine accepted and rejected targets
            if resolving_fact_id == fact_a.id:
                accepted_fact = fact_a
                rejected_fact = fact_b
            elif resolving_fact_id == fact_b.id:
                accepted_fact = fact_b
                rejected_fact = fact_a
            else:
                raise ValueError(f"Fact {resolving_fact_id} is not part of this conflict report.")

            # Status Transitions:
            # 1. Update accepted fact to verified
            accepted_fact.status = "verified"
            accepted_fact.updated_at = datetime.now(timezone.utc)

            # 2. Soft-delete rejected fact
            rejected_fact.deleted_at = datetime.now(timezone.utc)

            # 3. Update report status to resolved
            report.status = "resolved"
            report.resolved_by = user_id
            report.updated_at = datetime.now(timezone.utc)

            # Log CONFLICT_RESOLVED audit event
            event = ActivityEvent(
                user_id=user_id,
                project_id=report.project_id,
                action_name="CONFLICT_RESOLVED",
                payload={
                    "conflict_report_id": str(conflict_id),
                    "accepted_fact_id": str(accepted_fact.id),
                    "rejected_fact_id": str(rejected_fact.id),
                    "resolved_by_user_id": str(user_id)
                }
            )
            db.add(event)

        await db.commit()
        logger.info(f"Conflict report {conflict_id} resolved successfully.")
