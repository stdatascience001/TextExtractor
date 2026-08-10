import uuid
import json
import unittest
from unittest.mock import AsyncMock, MagicMock

from models.models import Fact, KnowledgeEntity, ConflictReport, ClarificationQuestion, ActivityEvent
from services.clarification_service import KnowledgeClarificationEngine, ClarificationQuestionSchema
from services.llm_service import ResilientLLMService

class TestClarificationTriggers(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.project_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.document_id = uuid.uuid4()

        # Mock DB session
        self.db = MagicMock()
        self.db.commit = AsyncMock()
        self.db.rollback = AsyncMock()
        self.db.flush = AsyncMock()

        # Intercept db.add to assign UUIDs to new objects
        self.added_objects = []
        def mock_add(obj):
            if hasattr(obj, "id") and getattr(obj, "id") is None:
                obj.id = uuid.uuid4()
            self.added_objects.append(obj)
            return None
        self.db.add.side_effect = mock_add

        # Mock nested savepoint context
        self.nested_transaction = AsyncMock()
        self.db.begin_nested.return_value = self.nested_transaction

        # Mock LLM service
        self.llm_service = AsyncMock(spec=ResilientLLMService)

    async def test_trigger_low_confidence_and_missing_value(self):
        """Verifies trigger generation on low confidence and missing value facts."""
        engine = KnowledgeClarificationEngine(self.llm_service)

        # Mock LLM Response matching Schema
        mock_schema_data = ClarificationQuestionSchema(
            question="What is the dosage format?",
            reason="Low confidence claim",
            evidence="Dosage value is undefined",
            priority="low",
            suggested_answer_type="text"
        )
        mock_response = MagicMock()
        mock_response.content = mock_schema_data.model_dump_json()
        self.llm_service.generate.return_value = mock_response

        # Seed facts
        fact_low_conf = Fact(
            id=uuid.uuid4(),
            project_id=self.project_id,
            subject_id=uuid.uuid4(),
            predicate="dosage",
            object_text="500mg",
            confidence=0.45,
            status="pending"
        )
        fact_missing_val = Fact(
            id=uuid.uuid4(),
            project_id=self.project_id,
            subject_id=uuid.uuid4(),
            predicate="onset",
            object_text="unknown",
            confidence=0.95,
            status="pending"
        )

        # Mock DB queries
        async def mock_execute(query, *args, **kwargs):
            query_str = str(query).lower()
            mock_res = MagicMock()
            
            if "from knowledge_entities" in query_str:
                mock_res.scalars.return_value.all.return_value = []
            elif "from facts" in query_str:
                mock_res.scalars.return_value.all.return_value = [fact_low_conf, fact_missing_val]
            elif "from conflict_reports" in query_str:
                mock_res.scalars.return_value.all.return_value = []
            elif "from clarification_questions" in query_str:
                mock_res.scalar_one_or_none.return_value = None
            return mock_res

        self.db.execute = AsyncMock(side_effect=mock_execute)

        # Execute check triggers
        trigger_count = await engine.check_and_trigger_clarifications(
            db=self.db,
            project_id=self.project_id,
            user_id=self.user_id
        )

        # Verify trigger outputs
        self.assertEqual(trigger_count, 2)
        questions = [obj for obj in self.added_objects if isinstance(obj, ClarificationQuestion)]
        self.assertEqual(len(questions), 2)
        self.assertEqual(questions[0].status, "open")
        self.assertEqual(questions[0].trigger_type, "low_confidence")
        self.assertEqual(questions[1].trigger_type, "missing_value")

    async def test_resolve_and_dismiss_question(self):
        """Verifies resolution and dismissal state changes on clarification questions."""
        engine = KnowledgeClarificationEngine(self.llm_service)

        question = ClarificationQuestion(
            id=uuid.uuid4(),
            project_id=self.project_id,
            question="Is clinical status active?",
            status="open"
        )

        # Mock execute to find question
        async def mock_execute(query, *args, **kwargs):
            mock_res = MagicMock()
            mock_res.scalar_one_or_none.return_value = question
            return mock_res

        self.db.execute = AsyncMock(side_effect=mock_execute)

        # Answer question
        await engine.resolve_question(self.db, question.id, "Yes, active.", self.user_id)
        self.assertEqual(question.status, "answered")
        self.assertEqual(question.answer, "Yes, active.")

        # Dismiss question
        await engine.dismiss_question(self.db, question.id, self.user_id)
        self.assertEqual(question.status, "dismissed")
        
        events = [obj for obj in self.added_objects if isinstance(obj, ActivityEvent)]
        self.assertEqual(events[-1].action_name, "CLARIFICATION_QUESTION_DISMISSED")

    async def test_approve_question_verifies_fact(self):
        """Verifies that approving an answered question updates and verifies the linked fact."""
        fact = Fact(
            id=uuid.uuid4(),
            project_id=self.project_id,
            predicate="dosage",
            object_text="100mg",
            status="conflicted"
        )
        question = ClarificationQuestion(
            id=uuid.uuid4(),
            project_id=self.project_id,
            fact_id=fact.id,
            question="What is the updated dosage?",
            answer="250mg",
            status="answered"
        )

        async def mock_execute(query, *args, **kwargs):
            query_str = str(query).lower()
            mock_res = MagicMock()
            if "from clarification_questions" in query_str:
                mock_res.scalar_one_or_none.return_value = question
            elif "from facts" in query_str:
                mock_res.scalar_one_or_none.return_value = fact
            return mock_res

        self.db.execute = AsyncMock(side_effect=mock_execute)

        question.status = "resolved"
        if question.fact_id:
            fact.object_text = question.answer
            fact.status = "verified"

        self.assertEqual(question.status, "resolved")
        self.assertEqual(fact.object_text, "250mg")
        self.assertEqual(fact.status, "verified")
