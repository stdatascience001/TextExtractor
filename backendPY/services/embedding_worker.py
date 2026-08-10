import asyncio
import logging
import uuid
import traceback
from datetime import datetime, timezone
from sqlalchemy import select

from database.database import SessionLocal
from models.models import Document, Page, Chunk, ActivityEvent

logger = logging.getLogger("embedding_worker")

class EmbeddingWorker:
    def __init__(self, interval_seconds: float = 3.0):
        self.interval_seconds = interval_seconds
        self._running = False
        self._task = None
        self._retry_tracker = {}  # document_id -> retry_count

    def start(self):
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Embedding Background Worker started.")

    async def stop(self):
        self._running = False
        if self._task:
            try:
                self._task.cancel()
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Embedding Background Worker stopped.")

    async def _run_loop(self):
        while self._running:
            try:
                await self.process_ready_documents()
            except Exception as e:
                logger.error(f"Error in embedding worker loop: {str(e)}")
            await asyncio.sleep(self.interval_seconds)

    async def process_ready_documents(self):
        async with SessionLocal() as db:
            # Query documents in "ready_for_embedding" status
            stmt = select(Document).where(Document.status == "ready_for_embedding").limit(5)
            res = await db.execute(stmt)
            docs = res.scalars().all()
            
            if not docs:
                return

            for doc in docs:
                doc_id = doc.id
                user_id = doc.user_id
                project_id = doc.project_id
                
                logger.info(f"Picked up document {doc_id} for asynchronous embedding generation.")
                doc.status = "embedding_running"
                doc.updated_at = datetime.now(timezone.utc)
                await db.commit()
                
                try:
                    # Query all chunk IDs for this document
                    chunk_stmt = (
                        select(Chunk.id)
                        .join(Page)
                        .where(Page.document_id == doc_id)
                    )
                    chunk_res = await db.execute(chunk_stmt)
                    chunk_ids = chunk_res.scalars().all()
                    
                    if chunk_ids:
                        from services.embedding_service import ingest_chunk_embeddings
                        await ingest_chunk_embeddings(db, chunk_ids, "nomic-embed-text")
                    
                    # Re-fetch document to ensure it is bound after prior commits in sub-services
                    stmt_refetch = select(Document).where(Document.id == doc_id)
                    res_refetch = await db.execute(stmt_refetch)
                    doc = res_refetch.scalar_one_or_none()
                    
                    if doc:
                        doc.status = "ready_for_validation"
                        doc.updated_at = datetime.now(timezone.utc)
                        await db.flush()

                    # Run Validation Engine
                    from services.validation_engine import ValidationEngine
                    validation_result = await ValidationEngine.validate_document(db, doc_id)

                    # Persist Processing Report
                    from services.report_generator import ProcessingReportGenerator
                    await ProcessingReportGenerator.generate_report(db, validation_result)

                    # Lifecycle transition
                    from services.lifecycle_manager import DocumentLifecycleManager
                    await DocumentLifecycleManager.transition_status(db, validation_result)
                    
                    # Atomic commit of the entire unit of work
                    await db.commit()
                except Exception as e:
                    await db.rollback()
                    stack_trace = traceback.format_exc()
                    logger.error(f"Error in pipeline sequence for document {doc_id}:\n{stack_trace}")
                    
                    # Track retry count and fallback to ready_for_embedding or failed
                    retry_count = self._retry_tracker.get(doc_id, 0) + 1
                    self._retry_tracker[doc_id] = retry_count
                    
                    # Re-query document to ensure it's fresh and bound to session
                    stmt_refetch = select(Document).where(Document.id == doc_id)
                    res_refetch = await db.execute(stmt_refetch)
                    doc = res_refetch.scalar_one_or_none()
                    
                    if doc:
                        if retry_count >= 3:
                            doc.status = "failed"
                        else:
                            doc.status = "ready_for_embedding"
                            
                        doc.updated_at = datetime.now(timezone.utc)
                        db.add(ActivityEvent(
                            user_id=user_id,
                            project_id=project_id,
                            action_name="EMBEDDING_STAGE_FAILED",
                            payload={
                                "document_id": str(doc_id),
                                "error": str(e),
                                "stack_trace": stack_trace,
                                "retry_count": retry_count
                            }
                        ))
                        await db.commit()

# Singleton worker instance
embedding_worker_instance = EmbeddingWorker()
