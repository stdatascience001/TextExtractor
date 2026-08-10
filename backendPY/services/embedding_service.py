import abc
import uuid
import hashlib
import logging
from typing import List, Dict, Any
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from database.database import SessionLocal
from models.models import Chunk, Embedding, AIJob

logger = logging.getLogger("embedding_service")

# 1. Embedding Adapter Interface
class EmbeddingAdapter(abc.ABC):
    @abc.abstractmethod
    def get_dimension(self) -> int:
        pass

    @abc.abstractmethod
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generates raw vector float arrays for the input list of text items."""
        pass

# 2. Deterministic Mock Embedding Generator Adapter
class MockEmbeddingAdapter(EmbeddingAdapter):
    """
    Produces deterministic pseudo-random unit vectors.
    Ensures consistent cosine similarities for search validation without third-party dependencies.
    """
    def __init__(self, model_name: str, dimension: int):
        self.model_name = model_name
        self.dimension = dimension

    def get_dimension(self) -> int:
        return self.dimension

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        vectors = []
        for text in texts:
            # Salt text with model name to ensure distinct dimensions are incompatible
            salted_input = f"{self.model_name}:{text}"
            hash_bytes = hashlib.sha256(salted_input.encode('utf-8')).digest()
            seed = int.from_bytes(hash_bytes[:4], byteorder='big')
            
            # Generate unit Gaussian vector
            rng = np.random.default_rng(seed)
            raw_vec = rng.standard_normal(self.dimension)
            norm = np.linalg.norm(raw_vec)
            
            if norm > 0:
                normalized_vec = raw_vec / norm
            else:
                normalized_vec = raw_vec
            
            vectors.append(normalized_vec.tolist())
        return vectors

# 3. Model Registry
class EmbeddingModelRegistry:
    _registry = {
        "all-MiniLM-L6-v2": {"dimension": 384},
        "nomic-embed-text": {"dimension": 768},
        "openai-text-embedding-3-small": {"dimension": 1536},
    }

    @classmethod
    def get_adapter(cls, model_name: str) -> EmbeddingAdapter:
        if model_name not in cls._registry:
            # Fallback default configuration
            logger.warning(f"Model {model_name} not registered. Defaulting to 768 dimensions.")
            return MockEmbeddingAdapter(model_name, 768)
        
        cfg = cls._registry[model_name]
        return MockEmbeddingAdapter(model_name, cfg["dimension"])

# 4. Batch Ingestion Writer
async def ingest_chunk_embeddings(db: AsyncSession, chunk_ids: List[uuid.UUID], model_name: str):
    """Ingests embeddings in batch sizes, mapping text inputs to vectors."""
    if not chunk_ids:
        return

    # Fetch chunks content
    stmt = select(Chunk).where(Chunk.id.in_(chunk_ids))
    res = await db.execute(stmt)
    chunks = res.scalars().all()
    
    if not chunks:
        return

    texts = [c.content for c in chunks]
    adapter = EmbeddingModelRegistry.get_adapter(model_name)
    vectors = adapter.generate_embeddings(texts)

    # Fetch existing embeddings for these chunks and this model in a single query
    stmt_existing = select(Embedding).where(
        and_(
            Embedding.chunk_id.in_(chunk_ids),
            Embedding.model_name == model_name
        )
    )
    res_existing = await db.execute(stmt_existing)
    existing_embeddings = {e.chunk_id: e for e in res_existing.scalars().all()}

    for chunk, vector in zip(chunks, vectors):
        existing = existing_embeddings.get(chunk.id)
        if existing:
            existing.embedding = vector
        else:
            embedding_obj = Embedding(
                chunk_id=chunk.id,
                embedding=vector,
                model_name=model_name
            )
            db.add(embedding_obj)

# 5. Background Re-indexing Pipeline Job
async def run_reindexing_job(job_id: uuid.UUID, target_model_name: str, batch_size: int = 32):
    """Asynchronous background worker executing zero-downtime model vector migration."""
    logger.info(f"Starting model re-indexing migration job {job_id} to model: {target_model_name}")
    
    async with SessionLocal() as db:
        # Update job status in database
        stmt = select(AIJob).where(AIJob.id == job_id)
        res = await db.execute(stmt)
        job = res.scalar_one_or_none()
        
        if job:
            job.status = "processing"
            await db.commit()

        try:
            # 1. Find all chunks that lack an embedding for target_model_name
            # We fetch IDs of chunks where no entry exists in embeddings table matching target_model_name
            subq = select(Embedding.chunk_id).where(Embedding.model_name == target_model_name)
            chunk_stmt = select(Chunk.id).where(Chunk.id.not_in(subq))
            
            chunk_res = await db.execute(chunk_stmt)
            unindexed_chunk_ids = chunk_res.scalars().all()
            
            total_chunks = len(unindexed_chunk_ids)
            logger.info(f"Re-indexing identified {total_chunks} unindexed chunks for model {target_model_name}")

            # 2. Process in batches
            for i in range(0, total_chunks, batch_size):
                batch_ids = unindexed_chunk_ids[i : i + batch_size]
                logger.info(f"Indexing batch {i // batch_size + 1}: processing {len(batch_ids)} chunks.")
                await ingest_chunk_embeddings(db, batch_ids, target_model_name)
                await db.commit()

            # 3. Create indices (HNSW vector mockup or relational index fallback)
            # Create standard index if running in Postgres array mode, or HNSW if Vector extension is present
            try:
                from sqlalchemy import text
                await db.execute(text("CREATE INDEX IF NOT EXISTS embeddings_model_idx ON embeddings (model_name);"))
                await db.commit()
            except Exception as idx_err:
                logger.warning(f"Could not build database indexes: {str(idx_err)}")

            # Update job to completed
            if job:
                job.status = "completed"
                await db.commit()
            logger.info(f"Re-indexing job {job_id} completed successfully.")

        except Exception as e:
            logger.exception(f"Error occurred during re-indexing job {job_id}")
            if job:
                job.status = "failed"
                job.error_message = str(e)
                await db.commit()
            raise e
