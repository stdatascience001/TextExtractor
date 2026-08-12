import uuid
import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from models.models import Chunk, DocumentElement, Page, Document

logger = logging.getLogger("layout_chunking_service")

class LayoutAwareChunkingService:
    @classmethod
    async def chunk_document(
        cls,
        db: AsyncSession,
        document_id: uuid.UUID,
        max_words: int = 400,
        overlap_words: int = 80
    ) -> int:
        """
        Groups DocumentElements into chunks sequentially.
        Ensures tables, lists, headings, code, and images are never split,
        and prepopulates chunks with element-level sliding window overlaps.
        """
        logger.info(f"Initiating layout-aware chunking for document {document_id}")

        # 1. Fetch all pages to map page_number -> page.id
        page_stmt = select(Page).where(Page.document_id == document_id)
        page_res = await db.execute(page_stmt)
        pages = page_res.scalars().all()
        if not pages:
            logger.warning(f"No pages found for document {document_id}. Skipping chunking.")
            return 0
        page_map = {p.page_number: p.id for p in pages}
        default_page_id = pages[0].id

        # 2. Fetch all elements sorted by reading order
        stmt = (
            select(DocumentElement)
            .where(DocumentElement.document_id == document_id)
            .order_by(DocumentElement.reading_order.asc())
        )
        res = await db.execute(stmt)
        elements = res.scalars().all()
        
        if not elements:
            logger.info(f"No document elements found for document {document_id}. Running text-based chunking fallback.")
            
            # Delete any pre-existing chunks for these pages (idempotency)
            page_ids = list(page_map.values())
            await db.execute(delete(Chunk).where(Chunk.page_id.in_(page_ids)))
            await db.commit()

            from services.chunking_service import ChunkingContext, LayoutAwareChunkingStrategy
            chunking_ctx = ChunkingContext(LayoutAwareChunkingStrategy())

            doc_stmt = select(Document).where(Document.id == document_id)
            doc_res = await db.execute(doc_stmt)
            doc_obj = doc_res.scalar_one_or_none()
            doc_name = doc_obj.file_name if doc_obj else "Document"

            chunk_count = 0
            for page in pages:
                chunks = chunking_ctx.chunk_page(
                    text=page.raw_text or "",
                    document_name=doc_name,
                    page_number=page.page_number,
                    target_tokens=500,
                    max_tokens=800,
                    overlap_tokens=100
                )
                for idx, chunk_content in enumerate(chunks):
                    chunk_obj = Chunk(
                        id=uuid.uuid4(),
                        page_id=page.id,
                        chunk_index=chunk_count,
                        content=chunk_content
                    )
                    db.add(chunk_obj)
                    chunk_count += 1
            
            await db.flush()
            logger.info(f"Fallback text-based chunking completed. Generated {chunk_count} chunks.")
            return chunk_count

        # Check if it is a spreadsheet document
        is_spreadsheet = any(el.element_type in ("sheet_header", "table_row") for el in elements)
        if is_spreadsheet:
            logger.info(f"Detected spreadsheet document {document_id}. Executing spreadsheet-aware chunking.")
            # Delete any pre-existing chunks for these pages (idempotency)
            page_ids = list(page_map.values())
            await db.execute(delete(Chunk).where(Chunk.page_id.in_(page_ids)))
            await db.commit()

            # Retrieve the document's file name
            doc_stmt = select(Document).where(Document.id == document_id)
            doc_res = await db.execute(doc_stmt)
            doc_obj = doc_res.scalar_one_or_none()
            doc_name = doc_obj.file_name if doc_obj else "Document"

            # Group elements by page_number
            from collections import defaultdict
            elements_by_page = defaultdict(list)
            for el in elements:
                elements_by_page[el.page_number].append(el)

            chunk_count = 0
            for page_num, page_elements in sorted(elements_by_page.items()):
                target_page_id = page_map.get(page_num, default_page_id)

                # Find sheet header
                sheet_header = next((el for el in page_elements if el.element_type == "sheet_header"), None)
                sheet_name = "Sheet"
                if sheet_header:
                    sheet_name = sheet_header.parsing_metadata.get("sheet_name", sheet_name)

                # Find table element to get headers
                table_el = next((el for el in page_elements if el.element_type == "table"), None)
                headers = []
                if table_el and table_el.parsing_metadata:
                    headers = table_el.parsing_metadata.get("headers", [])
                headers_str = ", ".join(str(h) for h in headers)

                # Get all table rows sorted by reading order
                table_rows = sorted(
                    [el for el in page_elements if el.element_type == "table_row"],
                    key=lambda r: r.reading_order
                )

                # Group rows in batches of N (e.g. 20)
                batch_size = 20
                for i in range(0, len(table_rows), batch_size):
                    batch = table_rows[i : i + batch_size]

                    chunk_lines = [f"[Document: {doc_name} | Sheet: {sheet_name} | Headers: {headers_str}]"]
                    for row_el in batch:
                        r_idx = row_el.parsing_metadata.get("row_index", "") if row_el.parsing_metadata else ""
                        row_text = row_el.content or ""
                        chunk_lines.append(f"Row {r_idx}: {row_text}")

                    chunk_content = "\n".join(chunk_lines)

                    chunk_obj = Chunk(
                        id=uuid.uuid4(),
                        page_id=target_page_id,
                        chunk_index=chunk_count,
                        content=chunk_content
                    )
                    db.add(chunk_obj)
                    chunk_count += 1

            await db.flush()
            logger.info(f"Spreadsheet chunking completed. Generated {chunk_count} chunks.")
            return chunk_count

        # Delete any pre-existing chunks for these pages (idempotency)
        page_ids = list(page_map.values())
        await db.execute(delete(Chunk).where(Chunk.page_id.in_(page_ids)))
        await db.commit()

        chunk_count = 0
        current_chunk_elements = []
        current_word_count = 0

        # Atomic block types that must not be split
        atomic_types = {"table", "bullet_list", "numbered_list", "heading", "code", "image", "caption", "formula", "footnote"}

        def finalize_and_save():
            nonlocal chunk_count
            if not current_chunk_elements:
                return
            
            content_str = "\n\n".join([el.content for el in current_chunk_elements if el.content.strip()])
            if not content_str.strip():
                return
            
            # Resolve target page_id
            page_num = current_chunk_elements[0].page_number
            target_page_id = page_map.get(page_num, default_page_id)
            
            chunk_obj = Chunk(
                id=uuid.uuid4(),
                page_id=target_page_id,
                chunk_index=chunk_count,
                content=content_str
            )
            db.add(chunk_obj)
            chunk_count += 1

        for el in elements:
            el_text = el.content or ""
            words = el_text.split()
            el_word_count = len(words)
            
            is_atomic = el.element_type in atomic_types
            
            # If adding this element would exceed max_words, finalize current chunk
            if current_chunk_elements and (current_word_count + el_word_count > max_words):
                finalize_and_save()
                
                # Prepopulate next chunk with overlap elements (sliding window)
                overlap_elements = []
                accum_overlap_words = 0
                for prev_el in reversed(current_chunk_elements):
                    prev_words = len((prev_el.content or "").split())
                    if accum_overlap_words + prev_words <= overlap_words:
                        overlap_elements.insert(0, prev_el)
                        accum_overlap_words += prev_words
                    else:
                        break
                
                current_chunk_elements = overlap_elements
                current_word_count = accum_overlap_words
            
            current_chunk_elements.append(el)
            current_word_count += el_word_count
            
            # If the added element is atomic (like a large table), finalize the chunk immediately
            # to keep it isolated as an atomic chunk boundary
            if is_atomic:
                finalize_and_save()
                current_chunk_elements = []
                current_word_count = 0

        # Save remaining buffer
        if current_chunk_elements:
            finalize_and_save()

        await db.flush()
        logger.info(f"Layout-aware chunking completed. Generated {chunk_count} chunks.")
        return chunk_count
