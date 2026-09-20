import math
import os
import json
from typing import List, Dict, Any, Optional
from backend.app.core.logging import logger
from backend.app.core.config import settings
from backend.app.rag.embeddings import EmbeddingService

class VectorSearchEngine:
    """
    Vector search engine for EASA DeskBot.
    Connects to Supabase pgvector if credentials configured,
    otherwise uses local persisted in-memory vector index.
    """
    def __init__(self, embedding_service: EmbeddingService = None):
        self.embedder = embedding_service or EmbeddingService()
        self.chunks: List[Dict[str, Any]] = []
        self.vectors: List[List[float]] = []
        self.supabase_client = None
        self._init_backend()

    def _init_backend(self):
        if settings.USE_SUPABASE:
            try:
                from supabase import create_client
                self.supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                logger.info("Connected to Supabase pgvector backend.")
            except Exception as e:
                logger.warning(f"Failed to connect to Supabase: {e}. Defaulting to local vector index.")

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        """Add and embed document chunks."""
        self.chunks.extend(chunks)
        texts = [c["content"] for c in chunks]
        embeddings = self.embedder.embed_documents(texts)
        self.vectors.extend(embeddings)
        logger.info(f"Vector search indexed {len(chunks)} chunks. Total: {len(self.chunks)}")

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_status: str = "current"
    ) -> List[Dict[str, Any]]:
        """Perform semantic vector retrieval."""
        query_vec = self.embedder.embed_query(query)
        
        # 1. Supabase pgvector RPC search
        if self.supabase_client:
            try:
                response = self.supabase_client.rpc(
                    "match_document_chunks",
                    {
                        "query_embedding": query_vec,
                        "match_count": top_k,
                        "filter_status": filter_status
                    }
                ).execute()
                if response.data:
                    return response.data
            except Exception as e:
                logger.warning(f"Supabase vector search failed: {e}. Using local store.")

        # 2. Local vector search with cosine similarity
        if not self.chunks:
            return []

        scored_results = []
        for chunk, vec in zip(self.chunks, self.vectors):
            meta = chunk.get("metadata", {})
            if filter_status and meta.get("status") != filter_status:
                continue

            similarity = self._cosine_similarity(query_vec, vec)
            # Boost priority (e.g. priority 10 gets slight positive bias over priority 2)
            priority = meta.get("priority", 8)
            boosted_sim = similarity * (1.0 + (priority - 8) * 0.03)

            scored_results.append({
                "content": chunk["content"],
                "metadata": meta,
                "vector_score": float(boosted_sim)
            })

        scored_results.sort(key=lambda x: x["vector_score"], reverse=True)
        return scored_results[:top_k]

    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return max(0.0, min(1.0, dot / (norm_a * norm_b)))
