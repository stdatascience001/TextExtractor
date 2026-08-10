import os
import time
import uuid
import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from models.models import Document, Page, Chunk, Embedding, DocumentElement
from services.embedding_service import EmbeddingModelRegistry

logger = logging.getLogger("retrieval_engine")

class RetrievedContext(BaseModel):
    original_query: str
    rewritten_query: str
    retrieved_chunks: List[str] = Field(default_factory=list)
    headings: List[str] = Field(default_factory=list)
    pages: List[int] = Field(default_factory=list)
    bounding_boxes: List[List[float]] = Field(default_factory=list)
    document_names: List[str] = Field(default_factory=list)
    document_ids: List[str] = Field(default_factory=list)
    retrieval_scores: Dict[str, float] = Field(default_factory=dict)
    keyword_matches: Dict[str, bool] = Field(default_factory=dict)
    retrieval_statistics: Dict[str, Any] = Field(default_factory=dict)
    timing_metrics: Dict[str, float] = Field(default_factory=dict)
    confidence_metrics: Dict[str, float] = Field(default_factory=dict)

# ----------------- Specialized Retrieval Components -----------------

class QueryProcessor:
    def process(self, query: str, conversation: Optional[List[Dict[str, str]]] = None) -> str:
        normalized = query.strip()
        if not normalized or not conversation:
            return normalized
        
        history_keywords = []
        for turn in conversation:
            content = turn.get("content", "")
            words = [w.strip().lower() for w in content.split() if len(w.strip()) > 4]
            history_keywords.extend(words)
        
        unique_kws = list(dict.fromkeys(history_keywords))[-5:]
        if unique_kws:
            return f"{normalized} {' '.join(unique_kws)}"
        return normalized

class EmbeddingProvider:
    def get_embedding(self, query: str) -> List[float]:
        active_model = os.getenv("ACTIVE_EMBEDDING_MODEL", "nomic-embed-text")
        adapter = EmbeddingModelRegistry.get_adapter(active_model)
        query_vectors = adapter.generate_embeddings([query])
        return query_vectors[0]

class BaseSearchStrategy(ABC):
    @abstractmethod
    async def search(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        query_vector: List[float],
        query_text: str,
        selected_documents: Optional[List[uuid.UUID]] = None,
        filters: Optional[Dict[str, Any]] = None,
        threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        pass

class VectorSearchStrategy(BaseSearchStrategy):
    async def search(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        query_vector: List[float],
        query_text: str,
        selected_documents: Optional[List[uuid.UUID]] = None,
        filters: Optional[Dict[str, Any]] = None,
        threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        active_model = os.getenv("ACTIVE_EMBEDDING_MODEL", "nomic-embed-text")
        stmt = (
            select(Chunk, Embedding, Page, Document)
            .join(Page, Chunk.page_id == Page.id)
            .join(Document, Page.document_id == Document.id)
            .join(Embedding, Embedding.chunk_id == Chunk.id)
            .where(
                and_(
                    Document.project_id == project_id,
                    Document.deleted_at.is_(None),
                    Embedding.model_name == active_model
                )
            )
        )
        if selected_documents:
            stmt = stmt.where(Document.id.in_(selected_documents))
        if filters:
            if "page_start" in filters:
                stmt = stmt.where(Page.page_number >= filters["page_start"])
            if "page_end" in filters:
                stmt = stmt.where(Page.page_number <= filters["page_end"])

        res = await db.execute(stmt)
        rows = res.all()
        
        # Keyword extraction
        q_lower = query_text.lower().replace("?", "").replace(".", "").replace("!", "").replace(",", "")
        stop_words = {"is", "there", "in", "this", "pdf", "does", "contain", "the", "a", "an", "of", "and", "to", "for", "with", "what", "how", "why", "who", "where", "when", "which", "are", "document", "about"}
        words = [w.strip() for w in q_lower.split() if w.strip()]
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        if not keywords:
            keywords = words

        candidates = []
        q_vec = np.array(query_vector)
        
        for chunk, embedding, page, doc in rows:
            e_vec = np.array(embedding.embedding)
            norm_q = np.linalg.norm(q_vec)
            norm_e = np.linalg.norm(e_vec)
            score = float(np.dot(q_vec, e_vec) / (norm_q * norm_e)) if (norm_q > 0 and norm_e > 0) else 0.0
            
            # Check for keyword exact match
            chunk_content_lower = (chunk.content or "").lower()
            keyword_matched = False
            if keywords:
                for kw in keywords:
                    if kw in chunk_content_lower:
                        keyword_matched = True
                        break
            
            # If keyword matches, we override score constraints
            if keyword_matched or score >= threshold:
                candidates.append({
                    "chunk": chunk,
                    "embedding": e_vec,
                    "page": page,
                    "document": doc,
                    "score": score,
                    "keyword_matched": keyword_matched
                })
        candidates.sort(key=lambda x: (x["keyword_matched"], x["score"]), reverse=True)
        return candidates

class MetadataFilter:
    async def resolve_layout_details(self, db: AsyncSession, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        resolved = []
        for item in items:
            chunk = item["chunk"]
            page = item["page"]
            doc = item["document"]
            
            bbox_coords = None
            parent_heading = None
            
            elem_stmt = select(DocumentElement).where(DocumentElement.document_id == doc.id)
            elem_res = await db.execute(elem_stmt)
            elements = elem_res.scalars().all()
            
            for el in elements:
                if el.content and len(el.content) > 20:
                    if el.content in chunk.content or chunk.content in el.content:
                        bbox_coords = el.bounding_box
                        if el.element_type == "heading":
                            parent_heading = el.content
                        elif el.parent_block_id:
                            parent_el = next((e for e in elements if e.block_id == el.parent_block_id), None)
                            if parent_el and parent_el.element_type == "heading":
                                parent_heading = parent_el.content
                        break
            
            item_copy = dict(item)
            item_copy["bbox"] = bbox_coords
            item_copy["heading"] = parent_heading
            resolved.append(item_copy)
        return resolved

class BaseDiversificationStrategy(ABC):
    @abstractmethod
    def diversify(
        self,
        candidates: List[Dict[str, Any]],
        query_vector: List[float],
        top_k: int,
        lambda_diversity: float
    ) -> List[Dict[str, Any]]:
        pass

class MMRDiversificationStrategy(BaseDiversificationStrategy):
    def diversify(
        self,
        candidates: List[Dict[str, Any]],
        query_vector: List[float],
        top_k: int,
        lambda_diversity: float
    ) -> List[Dict[str, Any]]:
        if not candidates:
            return []
            
        top_candidates = candidates[:25]
        selected = [top_candidates[0]]
        remaining = top_candidates[1:]
        
        while len(selected) < top_k and remaining:
            best_mmr = -100.0
            best_cand = None
            
            for cand in remaining:
                sim_to_query = cand["score"]
                sim_to_selected = max(
                    float(np.dot(cand["embedding"], sel["embedding"]) / 
                          (np.linalg.norm(cand["embedding"]) * np.linalg.norm(sel["embedding"])))
                    for sel in selected
                )
                mmr_score = lambda_diversity * sim_to_query - (1.0 - lambda_diversity) * sim_to_selected
                if mmr_score > best_mmr:
                    best_mmr = mmr_score
                    best_cand = cand
            
            if best_cand:
                selected.append(best_cand)
                remaining.remove(best_cand)
            else:
                break
        return selected

class BaseReranker(ABC):
    @abstractmethod
    def rerank(self, candidates: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        pass

class LexicalReranker(BaseReranker):
    def rerank(self, candidates: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        query_words = set(query.lower().split())
        for cand in candidates:
            chunk_words = set((cand["chunk"].content or "").lower().split())
            intersection_score = len(query_words.intersection(chunk_words))
            cand["score"] = cand["score"] * 0.7 + (intersection_score * 0.05) * 0.3
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates

class NeighborExpander:
    async def expand(self, db: AsyncSession, items: List[Dict[str, Any]], expand_neighbors: bool = True) -> List[Dict[str, Any]]:
        if not expand_neighbors:
            return items
            
        expanded = []
        for item in items:
            chunk = item["chunk"]
            page = item["page"]
            
            neighbor_stmt = (
                select(Chunk)
                .where(
                    and_(
                        Chunk.page_id == page.id,
                        Chunk.chunk_index.in_([chunk.chunk_index - 1, chunk.chunk_index + 1])
                    )
                )
            )
            neigh_res = await db.execute(neighbor_stmt)
            neighbors = neigh_res.scalars().all()
            
            pre_chunk = next((n for n in neighbors if n.chunk_index == chunk.chunk_index - 1), None)
            post_chunk = next((n for n in neighbors if n.chunk_index == chunk.chunk_index + 1), None)
            
            expanded_content = chunk.content
            if pre_chunk:
                expanded_content = f"{pre_chunk.content}\n\n{expanded_content}"
            if post_chunk:
                expanded_content = f"{expanded_content}\n\n{post_chunk.content}"
            
            item_copy = dict(item)
            item_copy["expanded_content"] = expanded_content
            expanded.append(item_copy)
        return expanded

class ContextCompressor:
    def compress(self, items: List[Dict[str, Any]], word_budget: int = 1500) -> List[Dict[str, Any]]:
        seen_ids = set()
        deduped = []
        for item in items:
            cid = item["chunk"].id
            if cid not in seen_ids:
                seen_ids.add(cid)
                deduped.append(item)
        
        compressed = []
        accum_words = 0
        for item in deduped:
            content = item.get("expanded_content", item["chunk"].content) or ""
            words = content.split()
            if accum_words + len(words) <= word_budget:
                compressed.append(item)
                accum_words += len(words)
            else:
                rem_words = word_budget - accum_words
                if rem_words > 20:
                    trimmed_content = " ".join(words[:rem_words]) + "..."
                    item_copy = dict(item)
                    item_copy["expanded_content"] = trimmed_content
                    compressed.append(item_copy)
                break
        return compressed

def merge_and_deduplicate(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen_ids = set()
    deduped_items = []
    for item in items:
        cid = item["chunk"].id
        if cid not in seen_ids:
            seen_ids.add(cid)
            deduped_items.append(item)
            
    if not deduped_items:
        return []
        
    deduped_items.sort(key=lambda x: (x["document"].id, x["page"].page_number, x["chunk"].chunk_index))
    
    merged_items = []
    current = deduped_items[0]
    
    for next_item in deduped_items[1:]:
        curr_chunk = current["chunk"]
        next_chunk = next_item["chunk"]
        
        if (current["document"].id == next_item["document"].id and 
            current["page"].page_number == next_item["page"].page_number and
            abs(curr_chunk.chunk_index - next_chunk.chunk_index) <= 1):
            
            curr_content = current.get("expanded_content", curr_chunk.content) or ""
            next_content = next_item.get("expanded_content", next_chunk.content) or ""
            
            if next_content not in curr_content:
                current["expanded_content"] = curr_content + "\n\n" + next_content
            
            curr_bbox = current.get("bbox")
            next_bbox = next_item.get("bbox")
            if curr_bbox and next_bbox:
                current["bbox"] = [
                    min(curr_bbox[0], next_bbox[0]),
                    min(curr_bbox[1], next_bbox[1]),
                    max(curr_bbox[2], next_bbox[2]),
                    max(curr_bbox[3], next_bbox[3])
                ]
            current["score"] = max(current["score"], next_item["score"])
            current["keyword_matched"] = current.get("keyword_matched", False) or next_item.get("keyword_matched", False)
        else:
            merged_items.append(current)
            current = next_item
            
    merged_items.append(current)
    return merged_items

class ContextAssembler:
    async def assemble(
        self,
        query: str,
        rewritten_query: str,
        items: List[Dict[str, Any]],
        timing_metrics: Dict[str, float]
    ) -> RetrievedContext:
        retrieved_chunks = []
        headings = []
        pages = []
        bounding_boxes = []
        document_names = []
        document_ids = []
        retrieval_scores = {}
        keyword_matches = {}
        
        for item in items:
            chunk = item["chunk"]
            content = item.get("expanded_content", chunk.content)
            retrieved_chunks.append(content)
            
            if item.get("heading"):
                headings.append(item["heading"])
            
            pages.append(item["page"].page_number)
            
            if item.get("bbox"):
                bounding_boxes.append(item["bbox"])
            
            document_names.append(item["document"].file_name)
            document_ids.append(str(item["document"].id))
                
            retrieval_scores[str(chunk.id)] = item["score"]
            keyword_matches[str(chunk.id)] = item.get("keyword_matched", False)
            
        ret_stats = {
            "total_retrieved_chunks": len(retrieved_chunks),
            "unique_pages_count": len(set(pages))
        }
        
        avg_score = sum(retrieval_scores.values()) / len(retrieval_scores) if retrieval_scores else 0.0
        confidence_metrics = {
            "average_similarity": avg_score,
            "retrieval_confidence": min(1.0, avg_score * 1.2)
        }

        return RetrievedContext(
            original_query=query,
            rewritten_query=rewritten_query,
            retrieved_chunks=retrieved_chunks,
            headings=list(set(headings)),
            pages=pages,
            bounding_boxes=bounding_boxes,
            document_names=document_names,
            document_ids=document_ids,
            retrieval_scores=retrieval_scores,
            keyword_matches=keyword_matches,
            retrieval_statistics=ret_stats,
            timing_metrics=timing_metrics,
            confidence_metrics=confidence_metrics
        )

# ----------------- Central Retrieval Orchestrator -----------------

class RetrievalEngine:
    def __init__(
        self,
        query_processor: Optional[QueryProcessor] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
        search_strategy: Optional[BaseSearchStrategy] = None,
        metadata_filter: Optional[MetadataFilter] = None,
        diversification_strategy: Optional[BaseDiversificationStrategy] = None,
        reranker: Optional[BaseReranker] = None,
        neighbor_expander: Optional[NeighborExpander] = None,
        context_compressor: Optional[ContextCompressor] = None,
        context_assembler: Optional[ContextAssembler] = None
    ):
        self.query_processor = query_processor or QueryProcessor()
        self.embedding_provider = embedding_provider or EmbeddingProvider()
        self.search_strategy = search_strategy or VectorSearchStrategy()
        self.metadata_filter = metadata_filter or MetadataFilter()
        self.diversification_strategy = diversification_strategy or MMRDiversificationStrategy()
        self.reranker = reranker or LexicalReranker()
        self.neighbor_expander = neighbor_expander or NeighborExpander()
        self.context_compressor = context_compressor or ContextCompressor()
        self.context_assembler = context_assembler or ContextAssembler()

    async def _retrieve_context_impl(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        query: str,
        conversation: Optional[List[Dict[str, str]]] = None,
        selected_documents: Optional[List[uuid.UUID]] = None,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
        threshold: float = 0.0,
        expand_neighbors: bool = True,
        lambda_diversity: float = 0.5
    ) -> RetrievedContext:
        start_time = time.time()
        
        # 1. Normalize & Rewrite Query
        t_start = time.time()
        rewritten_query = query.strip()
        if conversation:
            try:
                history_text = ""
                for msg in conversation[-5:]:
                    history_text += f"{msg['role'].upper()}: {msg['content']}\n"
                
                system_prompt = (
                    "You are a query rewriting assistant.\n"
                    "Given the conversation history and a follow-up user question, rewrite the follow-up user question to be a standalone, self-contained search query that captures the full context (e.g. resolve references like 'what about page 8?', 'this table', 'it').\n"
                    "Do NOT answer the question. Only output the rewritten search query. Keep it concise."
                )
                user_prompt = f"History:\n{history_text}\nFollow-up: {query}\nRewritten search query:"
                
                from services.prompt_builder import PromptPackage
                from domain.value_objects.llm import LLMSettings
                from services.llm_orchestrator import LLMOrchestrator
                
                settings = LLMSettings(project_id=project_id, user_id=None, temperature=0.0)
                rewrite_package = PromptPackage(system_prompt=system_prompt, user_prompt=user_prompt)
                
                res = await LLMOrchestrator.execute(
                    db=db,
                    logical_model_name="reasoning-heavy",
                    prompt_package=rewrite_package,
                    settings=settings,
                    timeout_seconds=5.0
                )
                rewritten_query = res.answer.strip()
            except Exception as e:
                logger.error(f"Failed to rewrite query via LLM: {str(e)}")
                rewritten_query = self.query_processor.process(query, conversation)
        else:
            rewritten_query = self.query_processor.process(query, conversation)
        t_process = time.time() - t_start
        
        # 2. Generate Embedding
        t_start = time.time()
        query_vector = self.embedding_provider.get_embedding(rewritten_query)
        t_embed = time.time() - t_start
        
        # 3. Vector Database Search
        t_start = time.time()
        candidates = await self.search_strategy.search(
            db=db,
            project_id=project_id,
            query_vector=query_vector,
            query_text=rewritten_query,
            selected_documents=selected_documents,
            filters=filters,
            threshold=threshold
        )
        t_search = time.time() - t_start
        
        # 4. Diversification (MMR)
        t_start = time.time()
        diversified = self.diversification_strategy.diversify(
            candidates=candidates,
            query_vector=query_vector,
            top_k=top_k,
            lambda_diversity=lambda_diversity
        )
        t_diversify = time.time() - t_start
        
        # 5. Rerank
        t_start = time.time()
        reranked = self.reranker.rerank(diversified, rewritten_query)
        t_rerank = time.time() - t_start
        
        # 6. Neighbor expansion
        t_start = time.time()
        expanded = await self.neighbor_expander.expand(db, reranked, expand_neighbors)
        t_expand = time.time() - t_start
        
        # 7. Context compression
        t_start = time.time()
        compressed = self.context_compressor.compress(expanded)
        t_compress = time.time() - t_start
        
        # 8. Resolve layout coordinates and headings
        t_start = time.time()
        resolved = await self.metadata_filter.resolve_layout_details(db, compressed)
        t_resolve = time.time() - t_start
        
        # 9. Timing metric collation
        timing_metrics = {
            "query_processor_seconds": t_process,
            "embedding_provider_seconds": t_embed,
            "search_strategy_seconds": t_search,
            "diversification_seconds": t_diversify,
            "rerank_seconds": t_rerank,
            "neighbor_expansion_seconds": t_expand,
            "context_compression_seconds": t_compress,
            "metadata_resolve_seconds": t_resolve,
            "total_retrieval_seconds": time.time() - start_time
        }
        
        # Merge overlapping chunks and deduplicate
        resolved = merge_and_deduplicate(resolved)

        result = await self.context_assembler.assemble(
            query=query,
            rewritten_query=rewritten_query,
            items=resolved,
            timing_metrics=timing_metrics
        )
        return result

    @classmethod
    async def retrieve_context(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        query: str,
        conversation: Optional[List[Dict[str, str]]] = None,
        selected_documents: Optional[List[uuid.UUID]] = None,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
        threshold: float = 0.0,
        expand_neighbors: bool = True,
        lambda_diversity: float = 0.5
    ) -> RetrievedContext:
        instance = cls()
        return await instance._retrieve_context_impl(
            db=db,
            project_id=project_id,
            query=query,
            conversation=conversation,
            selected_documents=selected_documents,
            filters=filters,
            top_k=top_k,
            threshold=threshold,
            expand_neighbors=expand_neighbors,
            lambda_diversity=lambda_diversity
        )
