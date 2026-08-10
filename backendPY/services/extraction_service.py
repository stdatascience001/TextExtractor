import uuid
import json
import logging
from typing import List, Dict, Any, Optional, Type
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from domain.value_objects.llm import LLMSettings
from models.models import Chunk, KnowledgeEntity, Fact, Evidence, ActivityEvent
from services.llm_service import ResilientLLMService, PromptRegistry

logger = logging.getLogger("extraction_service")

# 1. Pydantic schemas for structured extraction
class ExtractedEntity(BaseModel):
    name: str = Field(description="Name of the entity, e.g. Metformin or Diabetes")
    entity_type: str = Field(description="Category of the entity, e.g. drug, condition, test, etc.")
    description: Optional[str] = Field(default=None, description="Optional brief description or details.")

class ExtractedFact(BaseModel):
    subject_name: str = Field(description="Subject entity name, must match one of the extracted entity names")
    subject_type: str = Field(description="Subject entity type, must match the extracted entity type")
    predicate: str = Field(description="Relationship or action connecting subject and object, e.g. treats, indicates, dosage")
    object_value: str = Field(description="Object value or target details, e.g. Once daily, 500mg, elevated")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    evidence_verbatim: str = Field(description=" Verbatim text snippet from the input text chunk serving as source evidence")

class ExtractionResultSchema(BaseModel):
    entities: List[ExtractedEntity]
    facts: List[ExtractedFact]

# 2. Knowledge Extraction Engine
class KnowledgeExtractionEngine:
    def __init__(self, llm_service: ResilientLLMService):
        self.llm_service = llm_service

    async def extract_knowledge_from_chunk(
        self,
        db: AsyncSession,
        chunk_id: uuid.UUID,
        user_id: uuid.UUID,
        project_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Loads prompt templates, executes generation, corrects JSON formatting, resolves entities, and maps facts."""
        logger.info(f"Initiating knowledge extraction for chunk {chunk_id} in project {project_id}")

        # 1. Fetch chunk content
        chunk_stmt = select(Chunk).where(Chunk.id == chunk_id)
        chunk_res = await db.execute(chunk_stmt)
        chunk = chunk_res.scalar_one_or_none()
        if not chunk:
            raise ValueError(f"Chunk {chunk_id} not found in database.")

        # 2. Setup prompt and variables
        json_schema = json.dumps(ExtractionResultSchema.model_json_schema())
        variables = {
            "text": chunk.content,
            "json_schema": json_schema
        }

        # Attempt to load from prompt registry, falling back if not configured in db yet
        try:
            prompt = await PromptRegistry.get_prompt(db, "knowledge_extraction", variables)
        except Exception:
            sys_prompt = "You are a professional medical knowledge extraction agent. You parse patient reports and extract entities and facts as clean JSON."
            user_prompt = (
                f"Extract all entities and clinical facts from the following text according to the JSON schema:\n"
                f"{json_schema}\n\n"
                f"Text:\n{chunk.content}"
            )
            prompt = f"System Prompt:\n{sys_prompt}\n\nUser Message:\n{user_prompt}"

        # 3. Call LLM with Correction Loop
        settings = LLMSettings(
            temperature=0.0, # Minimum temperature for stable structured outputs
            json_mode=True,
            project_id=project_id,
            user_id=user_id
        )

        extracted_schema = await self._execute_extraction_with_correction(prompt, settings, max_corrections=3)

        # 4. Database Transaction & Deduplication Protocol
        resolved_entity_map = {} # Maps (name.lower(), type.lower()) -> Entity UUID
        
        # We wrap entity and fact writes inside a transaction savepoint
        async with db.begin_nested():
            # A. Resolve & Deduplicate Entities
            for ent in extracted_schema.entities:
                normalized_name = ent.name.strip()
                normalized_type = ent.entity_type.strip().lower()
                key = (normalized_name.lower(), normalized_type)
                
                # Check duplication in active project
                stmt = select(KnowledgeEntity).where(
                    and_(
                        KnowledgeEntity.project_id == project_id,
                        func.lower(KnowledgeEntity.name) == normalized_name.lower(),
                        func.lower(KnowledgeEntity.entity_type) == normalized_type
                    )
                )
                res = await db.execute(stmt)
                existing_entity = res.scalar_one_or_none()
                
                if existing_entity:
                    # Entity exists, reuse it. Update description if it was missing.
                    if not existing_entity.description and ent.description:
                        existing_entity.description = ent.description
                    resolved_entity_map[key] = existing_entity.id
                else:
                    # Create new entity record
                    new_entity = KnowledgeEntity(
                        project_id=project_id,
                        name=normalized_name,
                        entity_type=normalized_type,
                        description=ent.description
                    )
                    db.add(new_entity)
                    await db.flush() # Populate generated UUID
                    resolved_entity_map[key] = new_entity.id

            # B. Ingest Facts and Map Evidence References
            facts_count = 0
            inserted_facts = []
            for fact in extracted_schema.facts:
                subject_key = (fact.subject_name.strip().lower(), fact.subject_type.strip().lower())
                subject_uuid = resolved_entity_map.get(subject_key)
                
                if not subject_uuid:
                    # Skip or log orphan facts where subject resolution fails
                    logger.warning(f"Could not resolve entity subject {subject_key} for extracted fact: {fact.predicate}")
                    continue
                
                # Create Fact record
                new_fact = Fact(
                    project_id=project_id,
                    subject_id=subject_uuid,
                    predicate=fact.predicate.strip(),
                    object_text=fact.object_value.strip(),
                    confidence=fact.confidence,
                    status="unverified"
                )
                db.add(new_fact)
                await db.flush() # Populate generated UUID
                inserted_facts.append(new_fact)

                # Create Evidence mapping
                new_evidence = Evidence(
                    fact_id=new_fact.id,
                    chunk_id=chunk_id,
                    bounding_box={"verbatim": fact.evidence_verbatim}
                )
                db.add(new_evidence)
                facts_count += 1

            # Publish FactCreated events in outbox for asynchronous processing
            from services.outbox_service import OutboxService
            for fact in inserted_facts:
                await OutboxService.publish_fact_created(db, fact.id, project_id, user_id)

            # Log extraction event
            event = ActivityEvent(
                user_id=user_id,
                project_id=project_id,
                action_name="KNOWLEDGE_EXTRACTED",
                payload={"chunk_id": str(chunk_id), "facts_count": facts_count, "entities_count": len(extracted_schema.entities)}
            )
            db.add(event)
        
        # Commit parent scope
        await db.commit()
        logger.info(f"Successfully completed knowledge extraction: committed {len(extracted_schema.entities)} entities and {facts_count} facts.")
        
        return {
            "entities_count": len(extracted_schema.entities),
            "facts_count": facts_count
        }

    async def _execute_extraction_with_correction(
        self,
        prompt: str,
        settings: LLMSettings,
        max_corrections: int
    ) -> ExtractionResultSchema:
        """Runs the generation correction loop recursively if JSON schemas fail validations."""
        active_prompt = prompt

        for attempt in range(1, max_corrections + 1):
            try:
                response = await self.llm_service.generate("extraction-fast", active_prompt, settings)
                
                # Validate output json
                validated_data = ExtractionResultSchema.model_validate_json(response.content)
                return validated_data
            except Exception as validation_err:
                logger.warning(f"Schema validation failed on attempt {attempt}/{max_corrections}. Retrying with correction parameters... Error: {str(validation_err)}")
                if attempt == max_corrections:
                    raise validation_err
                
                # Feed error back into prompt context for correction
                active_prompt = (
                    f"{prompt}\n\n"
                    f"--- CORRECTION REQUEST ---\n"
                    f"Your previous JSON output failed validation with the following error:\n"
                    f"{str(validation_err)}\n\n"
                    f"Please output corrected JSON matching the schema strictly, resolving formatting issues."
                )
        
        raise ValueError("Failed to get valid extraction schema from LLM service.")
