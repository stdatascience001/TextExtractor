import uuid
import json
import unittest
from unittest.mock import AsyncMock, MagicMock

from models.models import Fact, KnowledgeEntity, ConflictReport, ActivityEvent, OutboxMessage
from services.conflict_service import KnowledgeConflictDetector, ConflictEvaluationSchema, RuleBasedConflictFilter
from services.llm_service import ResilientLLMService
from services.outbox_worker import OutboxWorker
from infrastructure.persistence.repositories.uow import SQLAlchemyUnitOfWork

class TestConflictDetection(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.project_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.subject_id = uuid.uuid4()

        # Mock DB session
        self.db = MagicMock()
        self.db.commit = AsyncMock()
        self.db.rollback = AsyncMock()
        self.db.flush = AsyncMock()

        # Mock nested savepoint transaction context
        self.nested_transaction = AsyncMock()
        self.db.begin_nested.return_value = self.nested_transaction

        # Intercept db.add to assign UUIDs to newly constructed model instances
        self.added_objects = []
        def mock_add(obj):
            if hasattr(obj, "id") and getattr(obj, "id") is None:
                obj.id = uuid.uuid4()
            self.added_objects.append(obj)
            return None
        self.db.add.side_effect = mock_add

        # Seed KnowledgeEntity Subject
        self.subject_entity = KnowledgeEntity(
            id=self.subject_id,
            project_id=self.project_id,
            name="Jane Doe",
            entity_type="patient"
        )

        # Mock LLM service
        self.llm_service = AsyncMock(spec=ResilientLLMService)

    def test_heuristics_normalization(self):
        """Verifies text normalization and unit stripping rules."""
        norm = RuleBasedConflictFilter.normalize_text("500 mg Daily")
        self.assertEqual(norm, "500")

        norm2 = RuleBasedConflictFilter.normalize_text("Tabs Metformin 1000g QD")
        self.assertEqual(norm2, "metformin 1000")

    def test_heuristics_matching(self):
        """Verifies rule-based conflict evaluations."""
        # Exact duplicate
        is_conflict, c_type = RuleBasedConflictFilter.evaluate_heuristic_match("Metformin 500mg daily", "Metformin 500mg daily")
        self.assertTrue(is_conflict)
        self.assertEqual(c_type, "duplicate")

        # Numeric mismatch
        is_conflict, c_type = RuleBasedConflictFilter.evaluate_heuristic_match("Metformin 500mg", "Metformin 1000mg")
        self.assertTrue(is_conflict)
        self.assertEqual(c_type, "numeric")

        # Temporal mismatch
        is_conflict, c_type = RuleBasedConflictFilter.evaluate_heuristic_match("Diagnosed in 2021", "Diagnosed in 2023")
        self.assertTrue(is_conflict)
        self.assertEqual(c_type, "temporal")

        # Needs semantic LLM check
        is_conflict, c_type = RuleBasedConflictFilter.evaluate_heuristic_match("Left lung mass", "Right lung lesion")
        self.assertFalse(is_conflict)
        self.assertEqual(c_type, "needs_llm")

    async def test_outbox_worker_runs_successfully(self):
        """Verifies outbox worker processes pending messages and resolves conflicts out-of-band."""
        worker = OutboxWorker(interval_seconds=0.1)

        # Mock Outbox message
        fact_id = uuid.uuid4()
        msg = OutboxMessage(
            id=uuid.uuid4(),
            event_type="FactCreated",
            payload={
                "fact_id": str(fact_id),
                "project_id": str(self.project_id),
                "user_id": str(self.user_id)
            },
            status="pending"
        )

        # Seed facts
        fact_a = Fact(
            id=uuid.uuid4(),
            project_id=self.project_id,
            subject_id=self.subject_id,
            predicate="status",
            object_text="Active disease state",
            confidence=0.9,
            status="pending"
        )
        fact_b = Fact(
            id=fact_id,
            project_id=self.project_id,
            subject_id=self.subject_id,
            predicate="status",
            object_text="In remission",
            confidence=0.95,
            status="pending"
        )

        # Mock database queries
        async def mock_execute(query, *args, **kwargs):
            query_str = str(query).lower()
            mock_res = MagicMock()
            
            if "from outbox_messages" in query_str:
                mock_res.scalars.return_value.all.return_value = [msg]
            elif "from facts" in query_str:
                if str(fact_id) in query_str:
                    mock_res.scalar_one_or_none.return_value = fact_b
                else:
                    mock_res.scalars.return_value.all.return_value = [fact_a]
            elif "from knowledge_entities" in query_str:
                mock_res.scalar_one_or_none.return_value = self.subject_entity
            elif "from conflict_reports" in query_str:
                mock_res.scalar_one_or_none.return_value = None
            return mock_res

        self.db.execute = AsyncMock(side_effect=mock_execute)

        # Mock LLM response
        mock_schema_data = ConflictEvaluationSchema(
            is_conflict=True,
            conflict_type="contradiction",
            reasoning="Disease status cannot be both active and in remission.",
            recommended_resolution="Verify history."
        )
        mock_response = MagicMock()
        mock_response.content = mock_schema_data.model_dump_json()
        self.llm_service.generate.return_value = mock_response

        # We need to monkey patch SessionLocal inside outbox_worker to use our mock db session
        from services import outbox_worker
        original_sessionmaker = outbox_worker.SessionLocal
        
        # Async context manager mock
        class SessionContext:
            async def __aenter__(self):
                return self._session
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
            def __init__(self, session):
                self._session = session
        
        outbox_worker.SessionLocal = lambda: SessionContext(self.db)

        try:
            # Trigger process loop
            await worker.process_pending_messages()

            # Verify Outbox Message completed
            self.assertEqual(msg.status, "completed")

            # Verify Facts locked to conflicted status
            self.assertEqual(fact_a.status, "conflicted")
            self.assertEqual(fact_b.status, "conflicted")

            # Verify Conflict Report populated with detailed fields
            reports = [obj for obj in self.added_objects if isinstance(obj, ConflictReport)]
            self.assertEqual(len(reports), 1)
            self.assertEqual(reports[0].conflict_type, "contradiction")
            self.assertEqual(reports[0].status, "open")
            self.assertIn("contradiction", reports[0].reasoning.lower())

            # Verify Activity Event CONFLICT_CREATED logged
            events = [obj for obj in self.added_objects if isinstance(obj, ActivityEvent)]
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].action_name, "CONFLICT_CREATED")
        finally:
            outbox_worker.SessionLocal = original_sessionmaker
