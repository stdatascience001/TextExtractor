import abc
import os
import uuid
import logging
import traceback
import fitz
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete

from models.models import (
    Document, Page, Chunk, Embedding, Fact, Evidence, ConflictReport, ClarificationQuestion, ActivityEvent, DocumentElement
)
from services.ocr_service import extract_text_from_image
from services.chunking_service import ChunkingContext, LayoutAwareChunkingStrategy
from services.layout_chunking_service import LayoutAwareChunkingService
from services.embedding_service import ingest_chunk_embeddings
from services.extraction_service import KnowledgeExtractionEngine
from services.conflict_service import KnowledgeConflictDetector
from services.clarification_service import KnowledgeClarificationEngine

logger = logging.getLogger("orchestrator")

# =====================================================================
# 1. DEPENDENCY INVERSION: Abstract Interfaces
# =====================================================================

class IOCRService(abc.ABC):
    @abc.abstractmethod
    def extract_pages(self, file_path: str, document_id: Optional[str] = None) -> List[Dict[str, Any]]:
        pass

class IChunkingService(abc.ABC):
    @abc.abstractmethod
    def chunk_page(self, text: str, document_name: str, page_number: int) -> List[str]:
        pass

class IEmbeddingService(abc.ABC):
    @abc.abstractmethod
    async def generate_and_save_embeddings(self, db: AsyncSession, chunk_ids: List[uuid.UUID], model_name: str):
        pass

class IExtractionService(abc.ABC):
    @abc.abstractmethod
    async def extract_knowledge(self, db: AsyncSession, chunk_id: uuid.UUID, user_id: uuid.UUID, project_id: uuid.UUID) -> Dict[str, Any]:
        pass

class IConflictService(abc.ABC):
    @abc.abstractmethod
    async def detect_conflicts(self, db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID) -> int:
        pass

class IClarificationService(abc.ABC):
    @abc.abstractmethod
    async def check_and_trigger(self, db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID, document_id: uuid.UUID) -> int:
        pass

# =====================================================================
# 2. CONCRETE ADAPTERS: Reusing existing services
# =====================================================================

class OCRServiceAdapter(IOCRService):
    def extract_pages(self, file_path: str, document_id: Optional[str] = None) -> List[Dict[str, Any]]:
        upload_dir = os.path.dirname(file_path)
        file_basename = os.path.basename(file_path)
        file_id = file_basename.split('.')[0]
        ext = file_basename.split('.')[-1].lower()
        
        pages_data = []
        if ext == "pdf":
            from core.config import settings
            from services.document_parser.docling_parser import DoclingParser
            from services.document_parser.pymupdf_parser import PyMuPDFParser
            
            use_docling = getattr(settings, "USE_DOCLING", True)
            parser = DoclingParser() if use_docling else PyMuPDFParser()
            
            doc_id = document_id or str(uuid.uuid4())
            try:
                parsed_doc = parser.parse(file_path, doc_id)
            except Exception as e:
                logger.error(f"[OCRServiceAdapter] Selected parser failed: {str(e)}. Falling back to PyMuPDF...")
                parser = PyMuPDFParser()
                parsed_doc = parser.parse(file_path, doc_id)
                
            # Render page previews (useful for highlighting region overlays)
            try:
                doc_fitz = fitz.open(file_path)
                for i, page_fitz in enumerate(doc_fitz, start=1):
                    image_name = f"{file_id}_page_{i}.png"
                    image_path_full = os.path.join(upload_dir, image_name)
                    if not os.path.exists(image_path_full):
                        pix = page_fitz.get_pixmap(matrix=fitz.Matrix(2, 2))
                        pix.save(image_path_full)
                    # Find page in parsed_doc and set image_path
                    matching_page = next((p for p in parsed_doc.document.pages if p.page_number == i), None)
                    if matching_page:
                        matching_page.image_path = f"/files/{image_name}"
            except Exception as render_err:
                logger.error(f"[OCRServiceAdapter] Failed to render page preview images: {str(render_err)}")

            self.last_parsed_doc = parsed_doc
            
            for page in parsed_doc.document.pages:
                page_text = "\n\n".join([item.text for item in page.items if item.text])
                img_path = page.image_path or ""
                if not img_path:
                    for item in page.items:
                        if item.metadata and "image_path" in item.metadata:
                            img_path = item.metadata["image_path"]
                            break
                        if item.image_path:
                            img_path = item.image_path
                            break
                
                pages_data.append({
                    "page_number": page.page_number,
                    "text": page_text,
                    "image_path": img_path
                })
        elif ext in ("jpg", "jpeg", "png"):
            text = extract_text_from_image(file_path)
            pages_data.append({
                "page_number": 1,
                "text": text,
                "image_path": f"/files/{file_basename}"
            })
        elif ext == "docx":
            from services.ocr_pipeline import parse_docx_text
            text = parse_docx_text(file_path)
            pages_data.append({
                "page_number": 1,
                "text": text,
                "image_path": ""
            })
        elif ext in ("txt", "csv"):
            from services.ocr_pipeline import parse_txt_text
            text = parse_txt_text(file_path)
            pages_data.append({
                "page_number": 1,
                "text": text,
                "image_path": ""
            })
        else:
            raise ValueError(f"Unsupported file extension: {ext}")
        return pages_data

class ChunkingServiceAdapter(IChunkingService):
    def __init__(self):
        self.ctx = ChunkingContext(LayoutAwareChunkingStrategy())
        
    def chunk_page(self, text: str, document_name: str, page_number: int) -> List[str]:
        return self.ctx.chunk_page(
            text=text,
            document_name=document_name,
            page_number=page_number,
            target_tokens=500,
            max_tokens=800,
            overlap_tokens=100
        )

class EmbeddingServiceAdapter(IEmbeddingService):
    async def generate_and_save_embeddings(self, db: AsyncSession, chunk_ids: List[uuid.UUID], model_name: str):
        await ingest_chunk_embeddings(db, chunk_ids, model_name)

class ExtractionServiceAdapter(IExtractionService):
    def __init__(self, engine: KnowledgeExtractionEngine):
        self.engine = engine
        
    async def extract_knowledge(self, db: AsyncSession, chunk_id: uuid.UUID, user_id: uuid.UUID, project_id: uuid.UUID) -> Dict[str, Any]:
        return await self.engine.extract_knowledge_from_chunk(db, chunk_id, user_id, project_id)

class ConflictServiceAdapter(IConflictService):
    def __init__(self, detector: KnowledgeConflictDetector):
        self.detector = detector
        
    async def detect_conflicts(self, db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID) -> int:
        return await self.detector.detect_and_report_conflicts(db, project_id, user_id)

class ClarificationServiceAdapter(IClarificationService):
    def __init__(self, engine: KnowledgeClarificationEngine):
        self.engine = engine
        
    async def check_and_trigger(self, db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID, document_id: uuid.UUID) -> int:
        return await self.engine.check_and_trigger_clarifications(db, project_id, user_id, document_id)

# =====================================================================
# 3. BACKEND ORCHESTRATOR
# =====================================================================

class DocumentOrchestrator:
    def __init__(
        self,
        ocr_service: IOCRService,
        chunking_service: IChunkingService,
        embedding_service: IEmbeddingService,
        extraction_service: IExtractionService,
        conflict_service: IConflictService,
        clarification_service: IClarificationService
    ):
        self.ocr_service = ocr_service
        self.chunking_service = chunking_service
        self.embedding_service = embedding_service
        self.extraction_service = extraction_service
        self.conflict_service = conflict_service
        self.clarification_service = clarification_service

    async def process_document(self, db: AsyncSession, document_id: uuid.UUID, file_path: str):
        """Runs the orchestrator pipeline sequentially supporting rollback and resumption."""
        stmt = select(Document).where(Document.id == document_id)
        res = await db.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            logger.error(f"Document {document_id} not found. Aborting.")
            return

        logger.info(f"Starting orchestration pipeline for document {document_id} (Initial state: {doc.status})")

        # Sequentially advance from current status
        while doc.status != "ready_for_embedding" and doc.status != "completed":
            current = doc.status

            if current in ("uploaded", "failed", "ocr_running"):
                await self._run_ocr(db, doc, file_path)
            elif current in ("ready_for_chunking", "ocr_completed", "chunking_running"):
                await self._run_chunking(db, doc)
            elif current == "chunking_completed" or current == "embedding_running":
                await self._run_embedding(db, doc)
            elif current == "embedding_completed" or current == "extraction_running":
                await self._run_extraction(db, doc)
            elif current == "extraction_completed" or current == "conflict_running":
                await self._run_conflict(db, doc)
            elif current == "conflict_completed" or current == "clarification_running":
                await self._run_clarification(db, doc)
            elif current == "clarification_completed":
                # Pipeline finished
                doc.status = "completed"
                doc.updated_at = datetime.now(timezone.utc)
                db.add(ActivityEvent(
                    user_id=doc.user_id,
                    project_id=doc.project_id,
                    action_name="DOCUMENT_PROCESSING_COMPLETED",
                    payload={"document_id": str(document_id)}
                ))
                await db.commit()
                logger.info(f"Orchestration completed successfully for document {document_id}")
                break
            else:
                logger.error(f"Unhandled document status: {current}")
                break

    # ----------------- OCR Stage -----------------
    async def _run_ocr(self, db: AsyncSession, doc: Document, file_path: str):
        doc_id = doc.id
        user_id = doc.user_id
        project_id = doc.project_id
        logger.info(f"[{doc_id}] Executing OCR Stage")
        doc.status = "ocr_running"
        await db.commit()

        try:
            # Rollback any prior page and element records (idempotency)
            await db.execute(delete(DocumentElement).where(DocumentElement.document_id == doc_id))
            await db.execute(delete(Page).where(Page.document_id == doc_id))
            await db.commit()

            # Execute OCR extraction
            pages_data = await asyncio.to_thread(self.ocr_service.extract_pages, file_path, str(doc.id))
            
            for p in pages_data:
                page_obj = Page(
                    document_id=doc.id,
                    page_number=p["page_number"],
                    image_path=p["image_path"],
                    raw_text=p["text"]
                )
                db.add(page_obj)
            await db.flush()

            # Create/update DocumentResult full text and structured_data
            from models.models import DocumentResult
            stmt_res = select(DocumentResult).where(DocumentResult.document_id == doc.id)
            res_result = await db.execute(stmt_res)
            doc_res = res_result.scalar_one_or_none()
            full_text = "\n".join([p["text"] for p in pages_data])
            
            # Fetch last_parsed_doc from adapter
            last_parsed_doc = getattr(self.ocr_service, "last_parsed_doc", None)
            structured_json = last_parsed_doc.model_dump() if last_parsed_doc else None
            
            if doc_res:
                doc_res.full_text = full_text
                if structured_json:
                    doc_res.structured_data = structured_json
            else:
                db.add(DocumentResult(
                    document_id=doc.id, 
                    full_text=full_text,
                    structured_data=structured_json
                ))
            await db.flush()

            # Save normalized DocumentElement rows if structured data exists
            if last_parsed_doc and last_parsed_doc.document and last_parsed_doc.document.pages:
                for page_info in last_parsed_doc.document.pages:
                    # Queue for traversing blocks in the page hierarchy (BFS)
                    queue = [(item, None) for item in page_info.items]
                    while queue:
                        item, p_id = queue.pop(0)
                        
                        meta = item.metadata or {}
                        parser_name = item.source_parser or "docling"
                        parser_version = meta.get("parser_version") or "1.0.0"
                        
                        db.add(DocumentElement(
                            id=uuid.uuid4(),
                            document_id=doc.id,
                            block_id=item.block_id,
                            page_number=item.page_number,
                            parent_block_id=p_id,
                            element_type=item.type,
                            content=item.text or "",
                            reading_order=item.reading_order,
                            bounding_box=item.bbox,
                            confidence=item.confidence,
                            parser_name=parser_name,
                            parser_version=parser_version,
                            parsing_metadata=meta
                        ))
                        
                        if item.children:
                            for child in item.children:
                                queue.append((child, item.block_id))
                                
                await db.flush()

            doc.status = "ready_for_chunking"
            db.add(ActivityEvent(
                user_id=doc.user_id,
                project_id=doc.project_id,
                action_name="OCR_STAGE_COMPLETED",
                payload={"document_id": str(doc.id), "pages_count": len(pages_data)}
            ))
            await db.commit()
        except Exception as e:
            await db.rollback()
            stack_trace = traceback.format_exc()
            logger.error(f"[{doc_id}] OCR Stage Failed:\n{stack_trace}")
            
            stmt_refetch = select(Document).where(Document.id == doc_id)
            res_refetch = await db.execute(stmt_refetch)
            doc = res_refetch.scalar_one_or_none()
            if doc:
                doc.status = "failed"
                doc.updated_at = datetime.now(timezone.utc)
            db.add(ActivityEvent(
                user_id=user_id,
                project_id=project_id,
                action_name="OCR_STAGE_FAILED",
                payload={"document_id": str(doc_id), "error": str(e), "stack_trace": stack_trace}
            ))
            await db.commit()
            raise e

    # ----------------- Chunking Stage -----------------
    async def _run_chunking(self, db: AsyncSession, doc: Document):
        doc_id = doc.id
        user_id = doc.user_id
        project_id = doc.project_id
        logger.info(f"[{doc_id}] Executing Chunking Stage")
        doc.status = "chunking_running"
        await db.commit()

        try:
            # Execute LayoutAwareChunkingService
            chunk_count = await LayoutAwareChunkingService.chunk_document(db, doc.id)

            doc.status = "ready_for_embedding"
            db.add(ActivityEvent(
                user_id=doc.user_id,
                project_id=doc.project_id,
                action_name="CHUNKING_STAGE_COMPLETED",
                payload={"document_id": str(doc.id), "chunks_count": chunk_count}
            ))
            await db.commit()
        except Exception as e:
            await db.rollback()
            stack_trace = traceback.format_exc()
            logger.error(f"[{doc_id}] Chunking Stage Failed:\n{stack_trace}")
            
            stmt_refetch = select(Document).where(Document.id == doc_id)
            res_refetch = await db.execute(stmt_refetch)
            doc = res_refetch.scalar_one_or_none()
            if doc:
                doc.status = "failed"
                doc.updated_at = datetime.now(timezone.utc)
            db.add(ActivityEvent(
                user_id=user_id,
                project_id=project_id,
                action_name="CHUNKING_STAGE_FAILED",
                payload={"document_id": str(doc_id), "error": str(e), "stack_trace": stack_trace}
            ))
            await db.commit()
            raise e

    # ----------------- Embedding Stage -----------------
    async def _run_embedding(self, db: AsyncSession, doc: Document):
        doc_id = doc.id
        user_id = doc.user_id
        project_id = doc.project_id
        logger.info(f"[{doc_id}] Executing Embedding Stage")
        doc.status = "embedding_running"
        await db.commit()

        try:
            # Query pages and chunks
            stmt_pages = select(Page.id).where(Page.document_id == doc.id)
            res_pages = await db.execute(stmt_pages)
            page_ids = res_pages.scalars().all()
            
            stmt_chunks = select(Chunk.id).where(Chunk.page_id.in_(page_ids))
            res_chunks = await db.execute(stmt_chunks)
            chunk_ids = res_chunks.scalars().all()

            # Rollback prior embeddings
            if chunk_ids:
                await db.execute(delete(Embedding).where(Embedding.chunk_id.in_(chunk_ids)))
                await db.commit()

            # Generate embeddings
            active_model = os.getenv("ACTIVE_EMBEDDING_MODEL", "nomic-embed-text")
            if chunk_ids:
                await self.embedding_service.generate_and_save_embeddings(db, chunk_ids, active_model)

            doc.status = "embedding_completed"
            db.add(ActivityEvent(
                user_id=doc.user_id,
                project_id=doc.project_id,
                action_name="EMBEDDING_STAGE_COMPLETED",
                payload={"document_id": str(doc.id), "chunks_count": len(chunk_ids), "model": active_model}
            ))
            await db.commit()
        except Exception as e:
            await db.rollback()
            stack_trace = traceback.format_exc()
            logger.error(f"[{doc_id}] Embedding Stage Failed:\n{stack_trace}")
            
            stmt_refetch = select(Document).where(Document.id == doc_id)
            res_refetch = await db.execute(stmt_refetch)
            doc = res_refetch.scalar_one_or_none()
            if doc:
                doc.status = "failed"
                doc.updated_at = datetime.now(timezone.utc)
            db.add(ActivityEvent(
                user_id=user_id,
                project_id=project_id,
                action_name="EMBEDDING_STAGE_FAILED",
                payload={"document_id": str(doc_id), "error": str(e), "stack_trace": stack_trace}
            ))
            await db.commit()
            raise e

    # ----------------- Knowledge Extraction Stage -----------------
    async def _run_extraction(self, db: AsyncSession, doc: Document):
        doc_id = doc.id
        user_id = doc.user_id
        project_id = doc.project_id
        logger.info(f"[{doc_id}] Executing Knowledge Extraction Stage")
        doc.status = "extraction_running"
        await db.commit()

        try:
            # Query chunk IDs
            stmt_pages = select(Page.id).where(Page.document_id == doc.id)
            res_pages = await db.execute(stmt_pages)
            page_ids = res_pages.scalars().all()
            
            stmt_chunks = select(Chunk.id).where(Chunk.page_id.in_(page_ids))
            res_chunks = await db.execute(stmt_chunks)
            chunk_ids = res_chunks.scalars().all()

            # Rollback facts and evidence
            if chunk_ids:
                stmt_ev = select(Evidence.fact_id).where(Evidence.chunk_id.in_(chunk_ids))
                res_ev = await db.execute(stmt_ev)
                fact_ids = res_ev.scalars().all()
                if fact_ids:
                    # Cascade deletes evidence automatically
                    await db.execute(delete(Fact).where(Fact.id.in_(fact_ids)))
                await db.commit()

            # Extract facts from each chunk concurrently with a Semaphore to limit concurrency
            from database.database import SessionLocal
            
            sem = asyncio.Semaphore(5)  # Limit parallel LLM calls to 5
            
            async def extract_chunk(cid: uuid.UUID):
                async with sem:
                    async with SessionLocal() as session:
                        try:
                            await self.extraction_service.extract_knowledge(session, cid, doc.user_id, doc.project_id)
                        except Exception as err:
                            logger.error(f"Concurrent extraction failed for chunk {cid}: {str(err)}")
                            raise err

            if chunk_ids:
                await asyncio.gather(*(extract_chunk(cid) for cid in chunk_ids))

            doc.status = "extraction_completed"
            db.add(ActivityEvent(
                user_id=doc.user_id,
                project_id=doc.project_id,
                action_name="EXTRACTION_STAGE_COMPLETED",
                payload={"document_id": str(doc.id)}
            ))
            await db.commit()
        except Exception as e:
            await db.rollback()
            stack_trace = traceback.format_exc()
            logger.error(f"[{doc_id}] Knowledge Extraction Stage Failed:\n{stack_trace}")
            
            stmt_refetch = select(Document).where(Document.id == doc_id)
            res_refetch = await db.execute(stmt_refetch)
            doc = res_refetch.scalar_one_or_none()
            if doc:
                doc.status = "failed"
                doc.updated_at = datetime.now(timezone.utc)
            db.add(ActivityEvent(
                user_id=user_id,
                project_id=project_id,
                action_name="EXTRACTION_STAGE_FAILED",
                payload={"document_id": str(doc_id), "error": str(e), "stack_trace": stack_trace}
            ))
            await db.commit()
            raise e

    # ----------------- Conflict Stage -----------------
    async def _run_conflict(self, db: AsyncSession, doc: Document):
        doc_id = doc.id
        user_id = doc.user_id
        project_id = doc.project_id
        logger.info(f"[{doc_id}] Executing Conflict Stage")
        doc.status = "conflict_running"
        await db.commit()

        try:
            # Query document facts
            stmt_pages = select(Page.id).where(Page.document_id == doc.id)
            res_pages = await db.execute(stmt_pages)
            page_ids = res_pages.scalars().all()
            stmt_chunks = select(Chunk.id).where(Chunk.page_id.in_(page_ids))
            res_chunks = await db.execute(stmt_chunks)
            chunk_ids = res_chunks.scalars().all()
            
            if chunk_ids:
                stmt_ev = select(Evidence.fact_id).where(Evidence.chunk_id.in_(chunk_ids))
                res_ev = await db.execute(stmt_ev)
                fact_ids = res_ev.scalars().all()
                if fact_ids:
                    # Rollback conflict reports involving these facts
                    await db.execute(delete(ConflictReport).where(
                        or_(
                            ConflictReport.first_fact_id.in_(fact_ids),
                            ConflictReport.second_fact_id.in_(fact_ids)
                        )
                    ))
                    await db.commit()

            # Execute conflict detection project-wide
            conf_count = await self.conflict_service.detect_conflicts(db, doc.project_id, doc.user_id)

            doc.status = "conflict_completed"
            db.add(ActivityEvent(
                user_id=doc.user_id,
                project_id=doc.project_id,
                action_name="CONFLICT_STAGE_COMPLETED",
                payload={"document_id": str(doc.id), "conflicts_found": conf_count}
            ))
            await db.commit()
        except Exception as e:
            await db.rollback()
            stack_trace = traceback.format_exc()
            logger.error(f"[{doc_id}] Conflict Stage Failed:\n{stack_trace}")
            
            stmt_refetch = select(Document).where(Document.id == doc_id)
            res_refetch = await db.execute(stmt_refetch)
            doc = res_refetch.scalar_one_or_none()
            if doc:
                doc.status = "failed"
                doc.updated_at = datetime.now(timezone.utc)
            db.add(ActivityEvent(
                user_id=user_id,
                project_id=project_id,
                action_name="CONFLICT_STAGE_FAILED",
                payload={"document_id": str(doc_id), "error": str(e), "stack_trace": stack_trace}
            ))
            await db.commit()
            raise e

    # ----------------- Clarification Stage -----------------
    async def _run_clarification(self, db: AsyncSession, doc: Document):
        doc_id = doc.id
        user_id = doc.user_id
        project_id = doc.project_id
        logger.info(f"[{doc_id}] Executing Clarification Stage")
        doc.status = "clarification_running"
        await db.commit()

        try:
            # Rollback clarification questions for this document
            await db.execute(delete(ClarificationQuestion).where(ClarificationQuestion.document_id == doc.id))
            await db.commit()

            # Trigger questions specifically for this document
            q_count = await self.clarification_service.check_and_trigger(db, doc.project_id, doc.user_id, doc.id)

            doc.status = "clarification_completed"
            db.add(ActivityEvent(
                user_id=doc.user_id,
                project_id=doc.project_id,
                action_name="CLARIFICATION_STAGE_COMPLETED",
                payload={"document_id": str(doc.id), "questions_generated": q_count}
            ))
            await db.commit()
        except Exception as e:
            await db.rollback()
            stack_trace = traceback.format_exc()
            logger.error(f"[{doc_id}] Clarification Stage Failed:\n{stack_trace}")
            
            stmt_refetch = select(Document).where(Document.id == doc_id)
            res_refetch = await db.execute(stmt_refetch)
            doc = res_refetch.scalar_one_or_none()
            if doc:
                doc.status = "failed"
                doc.updated_at = datetime.now(timezone.utc)
            db.add(ActivityEvent(
                user_id=user_id,
                project_id=project_id,
                action_name="CLARIFICATION_STAGE_FAILED",
                payload={"document_id": str(doc_id), "error": str(e), "stack_trace": stack_trace}
            ))
            await db.commit()
            raise e

# =====================================================================
# 4. ORCHESTRATION PIPELINE ENGINE RUNNER WITH RETRIES
# =====================================================================

async def run_orchestration_pipeline_with_retries(
    db: AsyncSession,
    document_id: uuid.UUID,
    file_path: str,
    max_retries: int = 3
):
    """Executes the pipeline with restart capability and automatic retries."""
    from database.database import SessionLocal
    from services.llm_service import ResilientLLMService
    
    logger.info(f"Initiating pipeline runner for document: {document_id}")
    
    # Instantiate concrete adapters
    llm_service = ResilientLLMService(None)
    
    ocr_service = OCRServiceAdapter()
    chunking_service = ChunkingServiceAdapter()
    embedding_service = EmbeddingServiceAdapter()
    extraction_service = ExtractionServiceAdapter(KnowledgeExtractionEngine(llm_service))
    conflict_service = ConflictServiceAdapter(KnowledgeConflictDetector(llm_service))
    clarification_service = ClarificationServiceAdapter(KnowledgeClarificationEngine(llm_service))

    orchestrator = DocumentOrchestrator(
        ocr_service=ocr_service,
        chunking_service=chunking_service,
        embedding_service=embedding_service,
        extraction_service=extraction_service,
        conflict_service=conflict_service,
        clarification_service=clarification_service
    )

    # Retry Loop
    for attempt in range(1, max_retries + 1):
        try:
            async with SessionLocal() as session:
                await orchestrator.process_document(session, document_id, file_path)
                return
        except Exception as err:
            logger.error(f"Attempt {attempt}/{max_retries} failed for document {document_id}: {str(err)}")
            if attempt == max_retries:
                logger.error(f"Orchestration pipeline exhausted all {max_retries} retries for document {document_id}")
                try:
                    async with SessionLocal() as session:
                        stmt = select(Document).where(Document.id == document_id)
                        res = await session.execute(stmt)
                        doc = res.scalar_one_or_none()
                        if doc:
                            doc.status = "failed"
                            await session.commit()
                except Exception as db_err:
                    logger.error(f"Could not mark document failed: {str(db_err)}")
                raise err
