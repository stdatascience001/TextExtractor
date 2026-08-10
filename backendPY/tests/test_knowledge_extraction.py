import os
import uuid
import unittest
from unittest.mock import AsyncMock, MagicMock

from models.models import Chunk, KnowledgeEntity, Fact, Evidence, ActivityEvent
from services.extraction_service import KnowledgeExtractionEngine, ExtractionResultSchema, ExtractedEntity, ExtractedFact
from services.llm_service import ResilientLLMService

class TestKnowledgeExtraction(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Seed variables
        self.chunk_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.project_id = uuid.uuid4()
        
        # Mock DB session
        self.db = MagicMock()
        self.db.commit = AsyncMock()
        self.db.rollback = AsyncMock()
        self.db.refresh = AsyncMock()
        self.db.flush = AsyncMock()
        
        # Setup nested savepoint transaction context
        self.nested_transaction = AsyncMock()
        self.db.begin_nested.return_value = self.nested_transaction

        # Intercept db.add to assign UUIDs to newly constructed model instances
        def mock_add(obj):
            if hasattr(obj, "id") and getattr(obj, "id") is None:
                obj.id = uuid.uuid4()
            return None
        self.db.add.side_effect = mock_add

        # Seed Chunk mock
        self.chunk = Chunk(
            id=self.chunk_id,
            page_id=uuid.uuid4(),
            chunk_index=1,
            content="Patient Jane Doe has severe atrial fibrillation. Metformin treats diabetes mellitus."
        )

        # Dynamic query inspector handler
        async def mock_execute(query, *args, **kwargs):
            query_str = str(query).lower()
            mock_res = MagicMock()
            
            if "from chunks" in query_str:
                mock_res.scalar_one_or_none.return_value = self.chunk
            elif "from knowledge_entities" in query_str:
                mock_res.scalar_one_or_none.return_value = None # Force creation
            elif "from prompt_templates" in query_str or "from prompt_versions" in query_str:
                mock_res.scalar_one_or_none.return_value = None # Fallback to default prompts
            else:
                mock_res.scalars.return_value.all.return_value = []
                mock_res.scalar_one_or_none.return_value = None
            return mock_res

        self.db.execute = AsyncMock(side_effect=mock_execute)

    async def test_knowledge_extraction_and_deduplication(self):
        # 1. Setup mock LLM response
        llm_service = AsyncMock(spec=ResilientLLMService)
        
        # Formulate fake LLM json response matching the schema
        mock_schema_data = ExtractionResultSchema(
            entities=[
                ExtractedEntity(name="Jane Doe", entity_type="patient", description="Seeded clinical patient"),
                ExtractedEntity(name="Metformin", entity_type="drug", description="Antidiabetic medication")
            ],
            facts=[
                ExtractedFact(
                    subject_name="Jane Doe",
                    subject_type="patient",
                    predicate="diagnosed_with",
                    object_value="atrial fibrillation",
                    confidence=0.95,
                    evidence_verbatim="Patient Jane Doe has severe atrial fibrillation"
                ),
                ExtractedFact(
                    subject_name="Metformin",
                    subject_type="drug",
                    predicate="treats",
                    object_value="diabetes mellitus",
                    confidence=0.99,
                    evidence_verbatim="Metformin treats diabetes mellitus"
                )
            ]
        )
        
        # Configure execute extraction output
        mock_fast_response = MagicMock()
        mock_fast_response.content = mock_schema_data.model_dump_json()
        llm_service.generate.return_value = mock_fast_response

        # 2. Instantiate Engine
        engine = KnowledgeExtractionEngine(llm_service)

        # 3. Execute extraction
        res = await engine.extract_knowledge_from_chunk(
            self.db,
            self.chunk_id,
            self.user_id,
            self.project_id
        )

        # 4. Assert database writes
        self.assertEqual(res["entities_count"], 2)
        self.assertEqual(res["facts_count"], 2)
        
        # Verify db.add was called for entities, facts, evidence, and activity log
        added_objects = [args[0] for args, _ in self.db.add.call_args_list]
        
        # Check added Entities
        added_entities = [o for o in added_objects if isinstance(o, KnowledgeEntity)]
        self.assertEqual(len(added_entities), 2)
        self.assertEqual(added_entities[0].name, "Jane Doe")
        self.assertEqual(added_entities[1].name, "Metformin")

        # Check added Facts
        added_facts = [o for o in added_objects if isinstance(o, Fact)]
        self.assertEqual(len(added_facts), 2)
        self.assertEqual(added_facts[0].predicate, "diagnosed_with")
        self.assertEqual(added_facts[1].predicate, "treats")

        # Check Evidence records
        added_evidences = [o for o in added_objects if isinstance(o, Evidence)]
        self.assertEqual(len(added_evidences), 2)

        # Check Ingestion Log Event
        added_events = [o for o in added_objects if isinstance(o, ActivityEvent)]
        self.assertEqual(len(added_events), 1)
        self.assertEqual(added_events[0].action_name, "KNOWLEDGE_EXTRACTED")

        # Assert transaction commits
        self.db.commit.assert_called_once()
        self.nested_transaction.__aenter__.assert_called_once()

if __name__ == "__main__":
    unittest.main()
