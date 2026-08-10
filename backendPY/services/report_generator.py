import uuid
import logging
import hashlib
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from models.models import Document, Page, Chunk, Embedding, DocumentElement, ProcessingReport
from services.validation_engine import ValidationResult

logger = logging.getLogger("report_generator")

class ProcessingReportGenerator:
    @classmethod
    async def generate_report(
        cls,
        db: AsyncSession,
        validation_result: ValidationResult,
        chunk_version: str = "1.0.0",
        embedding_version: str = "1.0.0"
    ) -> Optional[ProcessingReport]:
        """
        Generates and persists a detailed Document Processing Report based on the ValidationResult.
        Computes document and chunk text SHA-256 fingerprints, maps statistics, and records warnings.
        """
        doc_id = uuid.UUID(validation_result.document_id)
        logger.info(f"Generating persistent processing report for document {doc_id}")

        # 1. Retrieve document to verify registration
        stmt_doc = select(Document).where(Document.id == doc_id)
        doc_res = await db.execute(stmt_doc)
        doc = doc_res.scalar_one_or_none()

        if not doc:
            logger.warning(f"Document {doc_id} not found. Cannot generate processing report.")
            return None

        # 2. Compute processing duration
        start_time = doc.created_at
        now = datetime.now(timezone.utc)
        processing_time = (now - start_time).total_seconds()

        # 3. Compute Document Fingerprint
        doc_raw_data = f"{doc.file_name}_{doc.file_path}_{doc.created_at.isoformat()}"
        doc_fingerprint = hashlib.sha256(doc_raw_data.encode("utf-8")).hexdigest()

        # 4. Retrieve chunks to calculate chunk fingerprints
        stmt_chunks = select(Chunk).join(Page).where(Page.document_id == doc_id).order_by(Chunk.chunk_index.asc())
        chunks_res = await db.execute(stmt_chunks)
        chunks = chunks_res.scalars().all()

        chunk_fingerprints = []
        for chk in chunks:
            chk_content = chk.content or ""
            chk_hash = hashlib.sha256(chk_content.encode("utf-8")).hexdigest()
            chunk_fingerprints.append({
                "chunk_index": chk.chunk_index,
                "chunk_id": str(chk.id),
                "fingerprint": chk_hash
            })

        # 5. Retrieve parser and embedding version parameters
        stmt_elem = select(DocumentElement).where(DocumentElement.document_id == doc_id).limit(1)
        elem_res = await db.execute(stmt_elem)
        first_elem = elem_res.scalar_one_or_none()
        parser_version = first_elem.parser_version if first_elem else "1.0.0"

        stmt_emb = select(Embedding).join(Chunk).join(Page).where(Page.document_id == doc_id).limit(1)
        emb_res = await db.execute(stmt_emb)
        first_emb = emb_res.scalar_one_or_none()
        embedding_model = first_emb.model_name if first_emb else "nomic-embed-text"

        # 6. Map warnings and critical errors from ValidationResult
        warnings = [
            err.model_dump() for err in validation_result.errors if err.severity in ("warning", "minor")
        ]
        critical_errors = [
            err.model_dump() for err in validation_result.errors if err.severity in ("critical", "major")
        ]

        # 7. Format summary descriptor
        is_valid = validation_result.is_valid
        summary = (
            f"Pipeline validation report completed for {doc.file_name}. "
            f"Status: {'VALID' if is_valid else 'INVALID'}. "
            f"Contains {len(warnings)} warnings and {len(critical_errors)} errors."
        )

        # 8. Clean any pre-existing report for this document (idempotency)
        await db.execute(delete(ProcessingReport).where(ProcessingReport.document_id == doc_id))
        await db.flush()

        # 9. Create and save ProcessingReport
        report = ProcessingReport(
            id=uuid.uuid4(),
            document_id=doc_id,
            summary=summary,
            coverage=validation_result.coverage.model_dump(),
            statistics=validation_result.statistics.model_dump(),
            parser_version=parser_version,
            chunk_version=chunk_version,
            embedding_version=embedding_version,
            document_fingerprint=doc_fingerprint,
            chunk_fingerprints=chunk_fingerprints,
            embedding_model=embedding_model,
            processing_time=processing_time,
            warnings=warnings,
            critical_errors=critical_errors
        )
        db.add(report)
        await db.flush()
        
        logger.info(f"Processing report saved successfully for document {doc_id}. Report ID: {report.id}")
        return report
