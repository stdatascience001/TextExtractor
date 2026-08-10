import asyncio
import uuid
import unittest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from database.base import Base
from models.models import Project, Document, Page, Chunk, Fact, KnowledgeEntity, Evidence
from routes.projects import list_facts_for_review, batch_approve_facts, BatchApproveRequest

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

class TestReviewConsoleEndpoints(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(DATABASE_URL, echo=False)
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        self.db = self.SessionLocal()
        
        # Seed project and document
        self.project_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        
        project = Project(
            id=self.project_id,
            name="Review Console Test Project",
            description="Testing batch features"
        )
        self.db.add(project)
        await self.db.commit()

        doc = Document(
            project_id=self.project_id,
            user_id=self.user_id,
            file_name="chart.pdf",
            file_type="pdf",
            file_path="/files/chart.pdf",
            status="completed"
        )
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)

        page = Page(
            document_id=doc.id,
            page_number=1,
            image_path="",
            raw_text="Patient has mild hypertension."
        )
        self.db.add(page)
        await self.db.commit()
        await self.db.refresh(page)

        chunk = Chunk(
            page_id=page.id,
            chunk_index=0,
            content="Patient has mild hypertension."
        )
        self.db.add(chunk)
        await self.db.commit()
        await self.db.refresh(chunk)

        # Seed entity
        entity = KnowledgeEntity(
            project_id=self.project_id,
            name="John",
            entity_type="patient"
        )
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)

        # Seed two facts
        self.fact1 = Fact(
            project_id=self.project_id,
            subject_id=entity.id,
            predicate="condition",
            object_text="hypertension",
            confidence=0.8,
            status="unverified"
        )
        self.fact2 = Fact(
            project_id=self.project_id,
            subject_id=entity.id,
            predicate="status",
            object_text="active",
            confidence=0.9,
            status="unverified"
        )
        self.db.add(self.fact1)
        self.db.add(self.fact2)
        await self.db.commit()
        await self.db.refresh(self.fact1)
        await self.db.refresh(self.fact2)

        # Link evidence to fact1
        ev = Evidence(
            fact_id=self.fact1.id,
            chunk_id=chunk.id
        )
        self.db.add(ev)
        await self.db.commit()

    async def asyncTearDown(self):
        await self.db.close()
        await self.engine.dispose()

    async def test_list_facts_returns_evidence_citations(self):
        """Verifies review claims loader includes source citations."""
        res = await list_facts_for_review(self.project_id, current_user=None, db=self.db)
        self.assertEqual(len(res), 2)
        
        # Verify fact1 includes evidence
        fact1_payload = next(f for f in res if f["id"] == str(self.fact1.id))
        self.assertEqual(len(fact1_payload["evidence"]), 1)
        self.assertEqual(fact1_payload["evidence"][0]["document_name"], "chart.pdf")
        self.assertEqual(fact1_payload["evidence"][0]["page_number"], 1)

    async def test_batch_approve_workflow(self):
        """Verifies batch approving sets verified status for multiple claims."""
        req = BatchApproveRequest(fact_ids=[self.fact1.id, self.fact2.id])
        
        # Invoke route handler directly
        res = await batch_approve_facts(self.project_id, req, current_user=type('User', (object,), {'id': self.user_id}), db=self.db)
        self.assertEqual(res["status"], "ok")

        # Reload facts
        stmt = select(Fact).where(Fact.project_id == self.project_id)
        facts = (await self.db.execute(stmt)).scalars().all()
        for f in facts:
            self.assertEqual(f.status, "verified")
