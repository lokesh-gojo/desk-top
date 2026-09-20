from typing import List, Dict, Any, Tuple
from backend.app.core.logging import logger
from backend.app.core.config import settings

class EvidenceConfidenceGate:
    """
    Multi-signal evidence confidence evaluator for EASA DeskBot:
    Evaluates:
    - Vector semantic relevance
    - BM25 exact term relevance
    - Reranker aggregate score
    - Document status ('current' vs 'archived')
    - Source Authority ('official_notice' / 'official_webpage')
    - Evidence count
    
    If evidence is insufficient, aborts LLM invocation and triggers controlled fallback.
    """
    def __init__(self, min_confidence: float = None):
        self.min_confidence = min_confidence or settings.MIN_EVIDENCE_CONFIDENCE

    def evaluate(self, query: str, top_chunks: List[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
        """
        Evaluate confidence.
        Returns: (is_confident, confidence_summary)
        """
        if not top_chunks:
            return False, {
                "vector_score": 0.0,
                "bm25_score": 0.0,
                "rerank_score": 0.0,
                "overall_confidence": 0.0,
                "evidence_level": "insufficient",
                "source_authority": "none",
                "status": "none",
                "grounded": False
            }

        best_chunk = top_chunks[0]
        meta = best_chunk.get("metadata", {})
        
        vec_score = float(best_chunk.get("vector_score", 0.0))
        bm25_score = float(best_chunk.get("bm25_score", 0.0))
        rerank_score = float(best_chunk.get("rerank_score", 0.0))
        status = meta.get("status", "current")
        authority = meta.get("source_authority", "official_webpage")

        # Normalize metrics to 0-1 range
        norm_vec = min(1.0, max(0.0, vec_score))
        norm_bm25 = 1.0 if bm25_score > 5.0 else (bm25_score / 5.0 if bm25_score > 0 else 0.0)
        norm_rerank = min(1.0, max(0.0, rerank_score / 2.0))

        # Authority score
        auth_score = 1.0 if authority in ["official_notice", "official_webpage"] else 0.5
        status_score = 1.0 if status == "current" else 0.4

        # Composite multi-signal confidence formula
        composite_confidence = (
            (norm_vec * 0.45) +
            (norm_bm25 * 0.25) +
            (norm_rerank * 0.15) +
            (auth_score * 0.10) +
            (status_score * 0.05)
        )

        # Check keyword query alignment
        query_words = [w.lower() for w in query.split() if len(w) > 3]
        text_lower = best_chunk.get("content", "").lower()
        has_direct_terms = any(w in text_lower for w in query_words)
        
        if not has_direct_terms and norm_vec < 0.55:
            # Query terms are completely missing from retrieved text and vector similarity is low
            composite_confidence *= 0.6

        is_confident = composite_confidence >= self.min_confidence

        evidence_level = "strong" if composite_confidence >= 0.65 else ("moderate" if composite_confidence >= self.min_confidence else "insufficient")

        summary = {
            "vector_score": round(norm_vec, 3),
            "bm25_score": round(norm_bm25, 3),
            "rerank_score": round(norm_rerank, 3),
            "overall_confidence": round(composite_confidence, 3),
            "evidence_level": evidence_level,
            "source_authority": authority,
            "status": status,
            "grounded": is_confident
        }

        logger.info(f"Confidence Gate Result: {summary} (Pass: {is_confident})")
        return is_confident, summary
