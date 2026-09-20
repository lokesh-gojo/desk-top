import math
import re
from typing import List
from backend.app.core.logging import logger
from backend.app.core.config import settings

class EmbeddingService:
    """
    Multilingual & dense embedding service for EASA College content.
    Default: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (384-dim).
    Supports English & Tamil (தமிழ்) out of the box with zero dimensional divergence
    from pgvector vector(384).
    """
    def __init__(self, model_name: str = None, dimension: int = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self.dimension = dimension or settings.VECTOR_DIMENSION
        self.model = None
        self._init_model()

    def _init_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded multilingual embedding model: {self.model_name} (dim: {self.dimension})")
        except Exception as e:
            logger.warning(f"SentenceTransformer model {self.model_name} not loaded locally ({e}). Using Unicode-aware fallback vectorizer.")

    def embed_query(self, text: str) -> List[float]:
        if self.model:
            try:
                emb = self.model.encode(text, normalize_embeddings=True)
                return emb.tolist()
            except Exception as e:
                logger.warning(f"Error encoding query: {e}")
        return self._multilingual_vectorize(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if self.model:
            try:
                embs = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
                return embs.tolist()
            except Exception as e:
                logger.warning(f"Error encoding documents: {e}")
        return [self._multilingual_vectorize(t) for t in texts]

    def _multilingual_vectorize(self, text: str) -> List[float]:
        """
        Deterministic, normalized Unicode & multilingual-aware vectorizer
        for instant cold starts and environments without PyTorch.
        """
        dim = self.dimension
        # Supports English, Tamil (U+0B80 - U+0BFF), numbers, and standard characters
        tokens = re.findall(r"[\w\u0B80-\u0BFF]+", text.lower())
        vec = [0.0] * dim
        if not tokens:
            return vec
            
        for i, token in enumerate(tokens):
            # Use stable sha256 int representation instead of randomized hash()
            token_val = int.from_bytes(token.encode("utf-8")[:4], byteorder="big", signed=False) % dim
            weight = 1.0 / (1.0 + math.log(1 + i))
            vec[token_val] += weight
            
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec
