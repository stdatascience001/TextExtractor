import os
import uuid
import logging
from typing import List, Dict, Any
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from models.models import Document, Page, Chunk, Embedding
from services.embedding_service import EmbeddingModelRegistry

logger = logging.getLogger("search_service")

class HybridSearchEngine:
    @classmethod
    async def search(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        query_text: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Executes tenant-isolated vector and FTS search queries and merges results via Reciprocal Rank Fusion (RRF)."""
        logger.info(f"Executing hybrid search query '{query_text}' for project: {project_id}")

        if not query_text.strip():
            return []

        # 1. Fetch query vector using Active Model Adapter
        active_model = os.getenv("ACTIVE_EMBEDDING_MODEL", "nomic-embed-text")
        adapter = EmbeddingModelRegistry.get_adapter(active_model)
        query_vectors = adapter.generate_embeddings([query_text])
        query_vector = query_vectors[0]

        # 2. Vector Search (Cosine Similarity)
        # Query active chunks with embeddings matching the active model
        vec_stmt = (
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
        vec_res = await db.execute(vec_stmt)
        vec_rows = vec_res.all()

        vector_results = []
        q_vec = np.array(query_vector)

        for chunk, embedding, page, doc in vec_rows:
            e_vec = np.array(embedding.embedding)
            # Both query and storage vectors from our adapter are unit-normalized
            # So cosine similarity matches the dot product
            norm_q = np.linalg.norm(q_vec)
            norm_e = np.linalg.norm(e_vec)
            if norm_q > 0 and norm_e > 0:
                score = float(np.dot(q_vec, e_vec) / (norm_q * norm_e))
            else:
                score = 0.0

            vector_results.append({
                "chunk": chunk,
                "page": page,
                "document": doc,
                "score": score
            })

        # Sort vector results by similarity score descending (limit 20)
        vector_results.sort(key=lambda x: x["score"], reverse=True)
        vector_candidates = vector_results[:20]

        # 3. Lexical Keyword FTS Search
        # Split search terms to perform keyword frequency calculations
        keywords = [kw.strip().lower() for kw in query_text.split() if kw.strip()]
        
        lex_stmt = (
            select(Chunk, Page, Document)
            .join(Page, Chunk.page_id == Page.id)
            .join(Document, Page.document_id == Document.id)
            .where(
                and_(
                    Document.project_id == project_id,
                    Document.deleted_at.is_(None)
                )
            )
        )
        lex_res = await db.execute(lex_stmt)
        lex_rows = lex_res.all()

        lexical_results = []
        for chunk, page, doc in lex_rows:
            content_lower = chunk.content.lower()
            # Rank lexical match score based on sum of word frequencies
            score = sum(content_lower.count(kw) for kw in keywords)
            if score > 0:
                lexical_results.append({
                    "chunk": chunk,
                    "page": page,
                    "document": doc,
                    "score": score
                })

        # Sort lexical results descending (limit 20)
        lexical_results.sort(key=lambda x: x["score"], reverse=True)
        lexical_candidates = lexical_results[:20]

        # 4. Reciprocal Rank Fusion (RRF) Consolidation
        # RRF_Score = Sum( 1.0 / (60 + rank) )
        rrf_registry: Dict[uuid.UUID, Dict[str, Any]] = {}

        # Process Vector ranks
        for rank_idx, cand in enumerate(vector_candidates):
            cid = cand["chunk"].id
            rrf_score = 1.0 / (60.0 + (rank_idx + 1))
            rrf_registry[cid] = {
                "chunk": cand["chunk"],
                "page": cand["page"],
                "document": cand["document"],
                "rrf_score": rrf_score,
                "vector_rank": rank_idx + 1,
                "lexical_rank": None
            }

        # Process Lexical ranks
        for rank_idx, cand in enumerate(lexical_candidates):
            cid = cand["chunk"].id
            rrf_score = 1.0 / (60.0 + (rank_idx + 1))
            
            if cid in rrf_registry:
                rrf_registry[cid]["rrf_score"] += rrf_score
                rrf_registry[cid]["lexical_rank"] = rank_idx + 1
            else:
                rrf_registry[cid] = {
                    "chunk": cand["chunk"],
                    "page": cand["page"],
                    "document": cand["document"],
                    "rrf_score": rrf_score,
                    "vector_rank": None,
                    "lexical_rank": rank_idx + 1
                }

        # Sort combined results descending by RRF score
        consolidated = list(rrf_registry.values())
        consolidated.sort(key=lambda x: x["rrf_score"], reverse=True)
        
        # Select Top-K limits
        top_k_candidates = consolidated[:top_k]

        # 5. Format Citation details
        formatted_results = []
        for cand in top_k_candidates:
            chunk = cand["chunk"]
            page = cand["page"]
            doc = cand["document"]
            
            formatted_results.append({
                "chunk_id": str(chunk.id),
                "content": chunk.content,
                "chunk_index": chunk.chunk_index,
                "rrf_score": round(cand["rrf_score"], 6),
                "ranks": {
                    "vector": cand["vector_rank"],
                    "lexical": cand["lexical_rank"]
                },
                "citation": {
                    "document_id": str(doc.id),
                    "document_name": doc.file_name,
                    "page_number": page.page_number
                }
            })

        return formatted_results
