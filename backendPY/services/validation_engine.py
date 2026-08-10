import math
import uuid
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.models import Document, Page, Chunk, Embedding, DocumentElement, DocumentResult

logger = logging.getLogger("validation_engine")

class ValidationError(BaseModel):
    code: str
    severity: str  # critical, major, minor, warning
    message: str
    context: Dict[str, Any] = Field(default_factory=dict)

class ValidationStats(BaseModel):
    total_pages: int = 0
    total_elements: int = 0
    total_chunks: int = 0
    total_embeddings: int = 0
    words_count: int = 0

class ValidationCoverage(BaseModel):
    elements_chunked_ratio: float = 0.0
    chunks_embedded_ratio: float = 0.0

class ValidationResult(BaseModel):
    document_id: str
    is_valid: bool = True
    errors: List[ValidationError] = Field(default_factory=list)
    statistics: ValidationStats = Field(default_factory=ValidationStats)
    coverage: ValidationCoverage = Field(default_factory=ValidationCoverage)

class ValidationEngine:
    @classmethod
    async def validate_document(cls, db: AsyncSession, document_id: uuid.UUID) -> ValidationResult:
        """
        Executes extensive checks on a document's parsed pages, elements, chunks,
        and embeddings, returning a detailed validation result stateless report.
        """
        logger.info(f"Executing document pipeline validation for {document_id}")
        
        errors: List[ValidationError] = []
        stats = ValidationStats()
        coverage = ValidationCoverage()

        # ----------------- 1. Document Validation -----------------
        stmt_doc = select(Document).where(Document.id == document_id)
        doc_res = await db.execute(stmt_doc)
        doc = doc_res.scalar_one_or_none()

        if not doc:
            errors.append(ValidationError(
                code="DOC_NOT_FOUND",
                severity="critical",
                message=f"Document {document_id} was not found in the database."
            ))
            return ValidationResult(document_id=str(document_id), is_valid=False, errors=errors)

        if doc.status == "failed":
            errors.append(ValidationError(
                code="DOC_STATUS_FAILED",
                severity="critical",
                message="Document processing status is marked as failed."
            ))

        # Check metadata
        stmt_res = select(DocumentResult).where(DocumentResult.document_id == document_id)
        res_res = await db.execute(stmt_res)
        doc_res_record = res_res.scalar_one_or_none()
        if not doc_res_record or not doc_res_record.structured_data:
            errors.append(ValidationError(
                code="DOC_METADATA_MISSING",
                severity="minor",
                message="Structured document parser metadata is missing or incomplete."
            ))

        # ----------------- 2. Page Validation -----------------
        stmt_pages = select(Page).where(Page.document_id == document_id).order_by(Page.page_number.asc())
        pages_res = await db.execute(stmt_pages)
        pages = pages_res.scalars().all()
        stats.total_pages = len(pages)

        if not pages:
            errors.append(ValidationError(
                code="NO_PAGES_FOUND",
                severity="critical",
                message="No parsed page records were found for this document."
            ))
        else:
            page_numbers = [p.page_number for p in pages]
            # Check sequential page numbers (should start at 1, incrementing by 1)
            for idx, p_num in enumerate(page_numbers):
                expected = idx + 1
                if p_num != expected:
                    errors.append(ValidationError(
                        code="PAGE_NUMBER_GAP",
                        severity="major",
                        message=f"Page number gap detected. Expected page {expected}, found {p_num}.",
                        context={"expected": expected, "found": p_num}
                    ))
            
            # Check duplicates
            seen_pages = set()
            for p_num in page_numbers:
                if p_num in seen_pages:
                    errors.append(ValidationError(
                        code="DUPLICATE_PAGE_NUMBER",
                        severity="major",
                        message=f"Duplicate page number {p_num} detected.",
                        context={"page_number": p_num}
                    ))
                seen_pages.add(p_num)

        # ----------------- 3. Layout & Element Validation -----------------
        stmt_elems = select(DocumentElement).where(DocumentElement.document_id == document_id).order_by(DocumentElement.reading_order.asc())
        elems_res = await db.execute(stmt_elems)
        elements = elems_res.scalars().all()
        stats.total_elements = len(elements)

        element_ids = {el.block_id for el in elements}
        element_map = {el.block_id: el for el in elements}
        words_sum = 0

        for el in elements:
            words_sum += len((el.content or "").split())
            
            # Reading order check
            if el.reading_order < 0:
                errors.append(ValidationError(
                    code="INVALID_READING_ORDER",
                    severity="minor",
                    message=f"Element {el.block_id} has invalid reading order index: {el.reading_order}.",
                    context={"block_id": el.block_id, "reading_order": el.reading_order}
                ))

            # Bounding box check
            if el.bounding_box:
                bbox = el.bounding_box
                if not isinstance(bbox, list) or len(bbox) != 4:
                    errors.append(ValidationError(
                        code="INVALID_BBOX_FORMAT",
                        severity="minor",
                        message=f"Element {el.block_id} has malformed bounding box: {bbox}.",
                        context={"block_id": el.block_id, "bbox": bbox}
                    ))
                else:
                    left, bottom, right, top = bbox
                    if left > right or bottom > top:
                        errors.append(ValidationError(
                            code="INCONSISTENT_BBOX_BOUNDS",
                            severity="minor",
                            message=f"Element {el.block_id} bounding box coordinates are inconsistent: {bbox}.",
                            context={"block_id": el.block_id, "bbox": bbox}
                        ))

            # Parent-child check
            if el.parent_block_id:
                if el.parent_block_id not in element_ids:
                    errors.append(ValidationError(
                        code="ORPHAN_ELEMENT_PARENT",
                        severity="major",
                        message=f"Element {el.block_id} references non-existent parent block ID: {el.parent_block_id}.",
                        context={"block_id": el.block_id, "parent_block_id": el.parent_block_id}
                    ))
                else:
                    # Cycle detection
                    visited = set()
                    curr = el
                    has_cycle = False
                    while curr.parent_block_id:
                        if curr.block_id in visited:
                            has_cycle = True
                            break
                        visited.add(curr.block_id)
                        curr_parent = element_map.get(curr.parent_block_id)
                        if not curr_parent:
                            break
                        curr = curr_parent
                    
                    if has_cycle:
                        errors.append(ValidationError(
                            code="CYCLIC_ELEMENT_REFERENCE",
                            severity="major",
                            message=f"Cyclic reference chain detected starting at element: {el.block_id}.",
                            context={"block_id": el.block_id}
                        ))

            # Heading structure check
            # In a strict tree layout, elements like bullet list items or paragraphs shouldn't contain nested headings, etc.
            # But we can verify simple type mappings
            if el.element_type == "heading" and not el.content.strip():
                errors.append(ValidationError(
                    code="EMPTY_HEADING_ELEMENT",
                    severity="warning",
                    message=f"Heading element {el.block_id} has empty content text.",
                    context={"block_id": el.block_id}
                ))

        stats.words_count = words_sum

        # ----------------- 4. Chunk Validation -----------------
        page_ids = [p.id for p in pages]
        chunks: List[Chunk] = []
        if page_ids:
            stmt_chunks = select(Chunk).where(Chunk.page_id.in_(page_ids)).order_by(Chunk.chunk_index.asc())
            chunks_res = await db.execute(stmt_chunks)
            chunks = chunks_res.scalars().all()
        stats.total_chunks = len(chunks)

        seen_chunk_contents = set()
        for idx, chk in enumerate(chunks):
            # Check empty chunk
            if not chk.content or not chk.content.strip():
                errors.append(ValidationError(
                    code="EMPTY_CHUNK",
                    severity="major",
                    message=f"Chunk {chk.id} has empty or blank content.",
                    context={"chunk_id": str(chk.id)}
                ))
            else:
                # Check duplicate content
                text = chk.content.strip()
                if text in seen_chunk_contents:
                    errors.append(ValidationError(
                        code="DUPLICATE_CHUNK_CONTENT",
                        severity="warning",
                        message=f"Duplicate chunk text content detected for chunk {chk.id}.",
                        context={"chunk_id": str(chk.id)}
                    ))
                seen_chunk_contents.add(text)

            # Ordering check
            if chk.chunk_index != idx:
                errors.append(ValidationError(
                    code="INVALID_CHUNK_ORDERING",
                    severity="minor",
                    message=f"Chunk index ordering mismatch: expected {idx}, found {chk.chunk_index}.",
                    context={"chunk_id": str(chk.id), "expected": idx, "found": chk.chunk_index}
                ))

        # ----------------- 5. Embedding Validation -----------------
        chunk_ids = [chk.id for chk in chunks]
        embeddings: List[Embedding] = []
        if chunk_ids:
            stmt_embs = select(Embedding).where(Embedding.chunk_id.in_(chunk_ids))
            embs_res = await db.execute(stmt_embs)
            embeddings = embs_res.scalars().all()
        stats.total_embeddings = len(embeddings)

        for emb in embeddings:
            vector = emb.embedding
            # Check vector size and NaN / Zero detection
            if not vector:
                errors.append(ValidationError(
                    code="EMPTY_EMBEDDING_VECTOR",
                    severity="critical",
                    message=f"Embedding record {emb.id} contains empty vector.",
                    context={"embedding_id": str(emb.id)}
                ))
                continue

            # Nan or Inf checks
            has_nan = any(math.isnan(val) or math.isinf(val) for val in vector)
            if has_nan:
                errors.append(ValidationError(
                    code="EMBEDDING_NAN_DETECTION",
                    severity="critical",
                    message=f"NaN or Infinite float value detected inside vector {emb.id}.",
                    context={"embedding_id": str(emb.id)}
                ))

            # Zero vector check
            is_all_zeros = all(val == 0.0 for val in vector)
            if is_all_zeros:
                errors.append(ValidationError(
                    code="ZERO_EMBEDDING_VECTOR",
                    severity="major",
                    message=f"Zero vector detected for embedding record {emb.id}.",
                    context={"embedding_id": str(emb.id)}
                ))

            # Dimension checks (expecting 768 for nomic-embed-text)
            if len(vector) != 768:
                errors.append(ValidationError(
                    code="INVALID_EMBEDDING_DIMENSION",
                    severity="major",
                    message=f"Embedding {emb.id} dimension size mismatch: expected 768, found {len(vector)}.",
                    context={"embedding_id": str(emb.id), "found_dim": len(vector)}
                ))

        # ----------------- 6. Coverage Metric Computations -----------------
        # Ratio of elements accounted for in chunk text maps (approximation based on word distributions)
        if stats.total_elements > 0 and stats.total_chunks > 0:
            coverage.elements_chunked_ratio = min(1.0, stats.total_chunks / (stats.total_elements * 0.5))
        else:
            coverage.elements_chunked_ratio = 0.0

        if stats.total_chunks > 0:
            coverage.chunks_embedded_ratio = stats.total_embeddings / stats.total_chunks
        else:
            coverage.chunks_embedded_ratio = 0.0

        # Assess if document contains critical errors
        is_valid = not any(err.severity == "critical" for err in errors)

        return ValidationResult(
            document_id=str(document_id),
            is_valid=is_valid,
            errors=errors,
            statistics=stats,
            coverage=coverage
        )
