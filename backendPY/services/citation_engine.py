import re
import uuid
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from models.models import Document, Page, Chunk, DocumentElement
from services.retrieval_engine import RetrievedContext

logger = logging.getLogger("citation_engine")

class CitationItem(BaseModel):
    document_name: str
    document_id: Optional[str] = None
    page_number: int
    heading: Optional[str] = None
    bounding_box: Optional[List[float]] = None
    chunk_id: Optional[str] = None
    score: float

class CitationBundle(BaseModel):
    citations: List[CitationItem] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CitationEngine:
    @classmethod
    async def resolve_citations(
        cls,
        db: AsyncSession,
        retrieved_context: RetrievedContext,
        llm_response: str
    ) -> CitationBundle:
        """
        Parses inline citations from LLM response text, verifies their existence in the database,
        gathers coordinate regions, and resolves references to build a verified CitationBundle.
        """
        logger.info("Resolving response inline citations...")

        # 1. Parse inline bracket citations using regex
        # Pattern: [Doc: <doc_name>, Page: <page_number>]
        pattern = re.compile(r"\[Doc:\s*(.*?),\s*Page:\s*(\d+)\]")
        matches = pattern.findall(llm_response)

        if not matches:
            logger.info("No inline citations found in LLM response.")
            return CitationBundle()

        resolved_items: Dict[str, CitationItem] = {}

        for doc_name, page_num_str in matches:
            doc_name = doc_name.strip()
            page_number = int(page_num_str)

            # Query DB to verify document name and page number match
            stmt = (
                select(Chunk, Page, Document)
                .join(Page, Chunk.page_id == Page.id)
                .join(Document, Page.document_id == Document.id)
                .where(
                    and_(
                        Document.file_name == doc_name,
                        Page.page_number == page_number,
                        Document.deleted_at.is_(None)
                    )
                )
            )
            res = await db.execute(stmt)
            rows = res.all()

            if not rows:
                logger.warning(f"Citation validation failed: Document '{doc_name}' or page {page_number} not found.")
                continue

            # Resolve coordinates and headings from DocumentElements on same page
            first_chunk, first_page, first_doc = rows[0]
            bbox_coords = None
            heading_text = None
            best_chunk_id = str(first_chunk.id)
            best_score = 0.0

            # Match score from retrieved_context if active
            for chunk, page, doc in rows:
                cid_str = str(chunk.id)
                if cid_str in retrieved_context.retrieval_scores:
                    score = retrieved_context.retrieval_scores[cid_str]
                    if score > best_score:
                        best_score = score
                        best_chunk_id = cid_str

            # Find matching document element context
            elem_stmt = select(DocumentElement).where(
                and_(
                    DocumentElement.document_id == first_doc.id,
                    DocumentElement.page_number == page_number
                )
            )
            elem_res = await db.execute(elem_stmt)
            elements = elem_res.scalars().all()

            for el in elements:
                # Assign heading if matching layout heading
                if el.element_type == "heading" and not heading_text:
                    heading_text = el.content
                # Fetch bounding box
                if el.bounding_box and not bbox_coords:
                    bbox_coords = el.bounding_box

            # Unique key for deduplication
            ref_key = f"{first_doc.id}_{page_number}_{best_chunk_id}"
            
            if ref_key not in resolved_items or best_score > resolved_items[ref_key].score:
                resolved_items[ref_key] = CitationItem(
                    document_name=first_doc.file_name,
                    document_id=str(first_doc.id),
                    page_number=page_number,
                    heading=heading_text,
                    bounding_box=bbox_coords,
                    chunk_id=best_chunk_id,
                    score=round(best_score, 6)
                )

        citation_list = list(resolved_items.values())
        
        return CitationBundle(
            citations=citation_list,
            metadata={
                "total_parsed_matches": len(matches),
                "total_resolved_citations": len(citation_list)
            }
        )
