import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.models import Document, ActivityEvent
from services.validation_engine import ValidationResult

logger = logging.getLogger("lifecycle_manager")

class DocumentLifecycleManager:
    # In-memory retry tracker (document_id -> retry_count)
    _retry_tracker = {}

    @classmethod
    async def transition_status(
        cls,
        db: AsyncSession,
        validation_result: ValidationResult,
        max_retries: int = 3
    ) -> str:
        """
        Transitions the document state in PostgreSQL based on the validation result.
        - If valid: ready_for_chat
        - If invalid: ready_for_reindex (or failed if retry limit exceeded)
        """
        doc_id = uuid.UUID(validation_result.document_id)
        logger.info(f"Evaluating lifecycle transition for document {doc_id}")

        stmt = select(Document).where(Document.id == doc_id)
        res = await db.execute(stmt)
        doc = res.scalar_one_or_none()

        if not doc:
            logger.warning(f"Document {doc_id} not found in database. Aborting transition.")
            return "UNKNOWN"

        if validation_result.is_valid:
            # Clear retry count
            cls._retry_tracker.pop(doc_id, None)
            
            doc.status = "ready_for_chat"
            doc.updated_at = datetime.now(timezone.utc)
            db.add(ActivityEvent(
                user_id=doc.user_id,
                project_id=doc.project_id,
                action_name="LIFECYCLE_COMPLETED_SUCCESS",
                payload={"document_id": str(doc_id), "status": doc.status}
            ))
            await db.flush()
            logger.info(f"Document {doc_id} transitioned successfully to ready_for_chat.")
            return doc.status
        else:
            # Increment retry count
            retry_count = cls._retry_tracker.get(doc_id, 0) + 1
            cls._retry_tracker[doc_id] = retry_count
            
            if retry_count >= max_retries:
                doc.status = "failed"
                cls._retry_tracker.pop(doc_id, None)
            else:
                doc.status = "ready_for_reindex"
                
            doc.updated_at = datetime.now(timezone.utc)
            db.add(ActivityEvent(
                user_id=doc.user_id,
                project_id=doc.project_id,
                action_name="LIFECYCLE_COMPLETED_FAILURE",
                payload={"document_id": str(doc_id), "status": doc.status, "retry_count": retry_count}
            ))
            await db.flush()
            logger.warning(f"Document {doc_id} validation failed. Transitioned to status: {doc.status} (Retry attempt: {retry_count}/{max_retries}).")
            return doc.status
