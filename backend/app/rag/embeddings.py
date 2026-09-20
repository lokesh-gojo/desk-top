import math
import re
from typing import List
from backend.app.core.logging import logger
from backend.app.core.config import settings

class EmbeddingService:
    """
    Multilingual & dense embedding service for EASA College content.
    Supports SentenceTransformers (BGE-M3 / all-MiniLM-L6-v2) with
    resilient lightweight fallback for fast cloud container cold-starts.
    """
    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self.model = None
        self._init_model()

    def _init_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded embedding model: {self.model_name}")
        except Exception as e:
            logger.warning(f"SentenceTransformer not loaded ({e}). Using optimized internal vectorizer.")

    def embed_query(self, text: str) -> List[float]:
        if self.model:
            try:
                emb = self.model.encode(text, normalize_embeddings=True)
                return emb.tolist()
            except Exception as e:
                logger.warning(f"Error encoding query: {e}")
        return self._simple_vectorize(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if self.model:
            try:
                embs = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
                return embs.tolist()
            except Exception as e:
                logger.warning(f"Error encoding documents: {e}")
        return [self._simple_vectorize(t) for t in texts]

    def _simple_vectorize(self, text: str, dim: int = 384) -> List[float]:
        """Deterministic, normalized pseudo-embedding for zero-dependency container fallbacks."""
        words = re.findall(r"\w+", text.lower())
        vec = [0.0] * dim
        if not words:
            return vec
        for i, word in enumerate(words):
            val = hash(word) % dim
            vec[val] += 1.0 / (1.0 + math.log(1 + i))
            
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec
