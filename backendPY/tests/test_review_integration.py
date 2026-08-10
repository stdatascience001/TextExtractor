import asyncio
import uuid
import unittest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from database.base import Base
from models.models import Project, Document, Page, Chunk, Fact, KnowledgeEntity, Embedding, ActivityEvent
from services.review_service import KnowledgeReviewService

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

class TestReviewWorkflowIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # 1. Setup in-memory sqlite engine
        self.engine = create_async_engine(DATABASE_URL, echo=False)
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        self.db = self.SessionLocal()
        
        # 2. Seed data structures
        self.project_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        
        project = Project(
            id=self.project_id,
            name="Review Workflow Integration Test Project",
            description="Integration boundaries"
        )
        self.db.add(project)
        await self.db.commit()

        # Seed Document & Page for index search mocks
        self.doc = Document(
            project_id=self.project_id,
            user_id=self.user_id,
            file_name="patient_report.txt",
            file_type="text",
            file_path="/files/patient_report.txt",
            status="completed"
        )
        self.db.add(self.doc)
        await self.db.commit()
        await self.db.refresh(self.doc)

        self.page = Page(
            document_id=self.doc.id,
            page_number=1,
            image_path="",
            raw_text="Subject John has diabetes."
        )
        self.db.add(self.page)
        await self.db.commit()
        await self.db.refresh(self.page)

        # Seed entity
        self.entity = KnowledgeEntity(
            project_id=self.project_id,
            name="John Doe",
            entity_type="patient"
        )
        self.db.add(self.entity)
        await self.db.commit()
        await self.db.refresh(self.entity)

        # Seed Fact
        self.fact = Fact(
            project_id=self.project_id,
            subject_id=self.entity.id,
            predicate="diagnosis",
            object_text="Type 2 Diabetes",
            confidence=0.88,
            status="unverified"
        )
        self.db.add(self.fact)
        await self.db.commit()
        await self.db.refresh(self.fact)

    async def asyncTearDown(self):
        await self.db.close()
        await self.engine.dispose()

    async def test_approve_workflow_creates_index(self):
        """Verifies fact approval transitions status and syncs the vector search chunk index."""
        # 1. Execute Approve
        await KnowledgeReviewService.approve_fact(self.db, self.fact.id, self.user_id)
        
        # Reload fact
        stmt = select(Fact).where(Fact.id == self.fact.id)
        fact_reload = (await self.db.execute(stmt)).scalar_one()
        self.assertEqual(fact_reload.status, "verified")
        self.assertEqual(fact_reload.confidence, 1.0)

        # 2. Assert searchable pseudo-chunk was created
        chunk_stmt = select(Chunk).where(Chunk.content.like(f"Fact ID: {self.fact.id} -%"))
        chunk = (await self.db.execute(chunk_stmt)).scalar_one_or_none()
        self.assertIsNotNone(chunk)
        self.assertIn("John Doe diagnosis is Type 2 Diabetes", chunk.content)

        # 3. Assert embedding vectors exist
        emb_stmt = select(Embedding).where(Embedding.chunk_id == chunk.id)
        emb = (await self.db.execute(emb_stmt)).scalar_one_or_none()
        self.assertIsNotNone(emb)

    async def test_modify_workflow_updates_history(self):
        """Verifies fact modification updates status, search index chunk, and logs history state diffs."""
        # 1. Execute Modify
        await KnowledgeReviewService.modify_fact(
            self.db, 
            self.fact.id, 
            self.user_id, 
            new_predicate="treated_with", 
            new_object_text="Metformin"
        )

        # 2. Assert modifications saved
        stmt = select(Fact).where(Fact.id == self.fact.id)
        fact_reload = (await self.db.execute(stmt)).scalar_one()
        self.assertEqual(fact_reload.predicate, "treated_with")
        self.assertEqual(fact_reload.object_text, "Metformin")
        self.assertEqual(fact_reload.status, "verified")

        # 3. Assert search index chunk reflects modified values
        chunk_stmt = select(Chunk).where(Chunk.content.like(f"Fact ID: {self.fact.id} -%"))
        chunk = (await self.db.execute(chunk_stmt)).scalar_one_or_none()
        self.assertIsNotNone(chunk)
        self.assertIn("John Doe treated_with is Metformin", chunk.content)

        # 4. Assert modification activity event history logs exist
        event_stmt = select(ActivityEvent).where(ActivityEvent.action_name == "FACT_MODIFIED")
        event = (await self.db.execute(event_stmt)).scalar_one_or_none()
        self.assertIsNotNone(event)
        self.assertEqual(event.payload["prior_state"]["predicate"], "diagnosis")
        self.assertEqual(event.payload["prior_state"]["object_text"], "Type 2 Diabetes")

    async def test_reject_workflow_cleans_index(self):
        """Verifies fact rejection soft-deletes and cleans virtual index chunk vectors."""
        # Setup verified first to index it
        await KnowledgeReviewService.approve_fact(self.db, self.fact.id, self.user_id)
        
        # Verify index exists
        chunk_stmt = select(Chunk).where(Chunk.content.like(f"Fact ID: {self.fact.id} -%"))
        chunk = (await self.db.execute(chunk_stmt)).scalar_one_or_none()
        self.assertIsNotNone(chunk)

        # Reject it
        await KnowledgeReviewService.reject_fact(self.db, self.fact.id, self.user_id)

        # Re-query index chunk: should be removed
        chunk_after = (await self.db.execute(chunk_stmt)).scalar_one_or_none()
        self.assertIsNone(chunk_after)

    async def test_undo_action_reverts_values(self):
        """Verifies that undoing a modification reverts both the values and index content."""
        # 1. Modify
        await KnowledgeReviewService.modify_fact(
            self.db, 
            self.fact.id, 
            self.user_id, 
            new_predicate="status", 
            new_object_text="Remission"
        )
        
        # 2. Undo
        await KnowledgeReviewService.undo_last_action(self.db, self.fact.id, self.user_id)

        # Reload
        stmt = select(Fact).where(Fact.id == self.fact.id)
        fact_reload = (await self.db.execute(stmt)).scalar_one()
        self.assertEqual(fact_reload.predicate, "diagnosis")
        self.assertEqual(fact_reload.object_text, "Type 2 Diabetes")
        self.assertEqual(fact_reload.status, "unverified")

        # Index chunk should be removed since status is reverted to unverified
        chunk_stmt = select(Chunk).where(Chunk.content.like(f"Fact ID: {self.fact.id} -%"))
        chunk = (await self.db.execute(chunk_stmt)).scalar_one_or_none()
        self.assertIsNone(chunk)
