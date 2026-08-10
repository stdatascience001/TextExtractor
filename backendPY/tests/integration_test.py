import asyncio
import uuid
import unittest
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from sqlalchemy import select
from database.base import Base
from models.models import Project, Document, Page, Chunk, Fact, KnowledgeEntity, ConflictReport
from services.chunking_service import ChunkingContext, LayoutAwareChunkingStrategy
from services.embedding_service import ingest_chunk_embeddings
from services.extraction_service import KnowledgeExtractionEngine
from services.conflict_service import KnowledgeConflictDetector
from services.generation_service import DocumentGenerationEngine
from services.llm_service import ResilientLLMService

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

class TestEndToEndKnowledgePipeline(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # 1. Setup in-memory sqlite engine for testing
        self.engine = create_async_engine(DATABASE_URL, echo=False)
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        self.db = self.SessionLocal()
        
        # 2. Seed project and user workspace details
        self.project_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        
        project = Project(
            id=self.project_id,
            name="Clinical Test Project",
            description="Testing integration pipeline boundaries"
        )
        self.db.add(project)
        await self.db.commit()

    async def asyncTearDown(self):
        await self.db.close()
        await self.engine.dispose()

    async def test_full_ingestion_to_report_compilation(self):
        """End-to-end pipeline validation of parsing, chunking, extracting, conflict checking, and compiling."""
        # A. Create parsed document text pages
        doc = Document(
            project_id=self.project_id,
            user_id=self.user_id,
            file_name="patient_chart_v1.txt",
            file_type="text",
            file_path="/files/patient_chart_v1.txt"
        )
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)

        raw_page_text = (
            "# Patient Information\n"
            "Patient name: Jane Doe. Age: 45.\n\n"
            "# Clinical Findings\n"
            "Patient exhibits elevated hemoglobin levels at 16.5 g/dL. Diagnosed with mild anemia."
        )
        
        page = Page(
            document_id=doc.id,
            page_number=1,
            image_path="",
            raw_text=raw_page_text
        )
        self.db.add(page)
        await self.db.commit()
        await self.db.refresh(page)

        # B. Segment pages using Layout-Aware Chunker
        chunking_ctx = ChunkingContext(LayoutAwareChunkingStrategy())
        chunks = chunking_ctx.chunk_page(
            text=page.raw_text,
            document_name=doc.file_name,
            page_number=1,
            target_tokens=100,
            max_tokens=200,
            overlap_tokens=10
        )
        
        self.assertEqual(len(chunks) > 0, True)
        
        chunk_objects = []
        for idx, content in enumerate(chunks):
            chunk_obj = Chunk(
                page_id=page.id,
                chunk_index=idx,
                content=content
            )
            self.db.add(chunk_obj)
            chunk_objects.append(chunk_obj)
            
        await self.db.commit()
        for c in chunk_objects:
            await self.db.refresh(c)

        # C. Generate mock vectors in batch
        chunk_ids = [c.id for c in chunk_objects]
        await ingest_chunk_embeddings(self.db, chunk_ids, "nomic-embed-text")
        await self.db.commit()

        # D. Execute AI Knowledge Extraction Engine
        llm_service = ResilientLLMService(self.db)
        extraction_engine = KnowledgeExtractionEngine(llm_service)
        
        for c in chunk_objects:
            await extraction_engine.extract_knowledge_from_chunk(
                db=self.db,
                chunk_id=c.id,
                user_id=self.user_id,
                project_id=self.project_id
            )

        # Verify entities and facts exist
        ent_res = await self.db.execute(select(KnowledgeEntity).where(KnowledgeEntity.project_id == self.project_id))
        entities = ent_res.scalars().all()
        self.assertEqual(len(entities) > 0, True)

        fact_res = await self.db.execute(select(Fact).where(Fact.project_id == self.project_id))
        facts = fact_res.scalars().all()
        self.assertEqual(len(facts) > 0, True)

        # E. AI Conflict Detection
        conflict_detector = KnowledgeConflictDetector(llm_service)
        conf_count = await conflict_detector.detect_and_report_conflicts(self.db, self.project_id, self.user_id)
        self.assertEqual(isinstance(conf_count, int), True)

        # F. Re-verify facts to trigger report compiles
        for f in facts:
            f.status = "verified"
            f.confidence = 1.0
        await self.db.commit()

        # G. Compile verified documents
        gen_doc = await DocumentGenerationEngine.generate_document(
            db=self.db,
            project_id=self.project_id,
            user_id=self.user_id,
            template_name="clinical_summary",
            export_format="html",
            document_name="Patient_Jane_Doe_Summary"
        )
        self.assertIsNotNone(gen_doc.id)
        self.assertEqual(gen_doc.name, "Patient_Jane_Doe_Summary.html")

if __name__ == "__main__":
    unittest.main()
