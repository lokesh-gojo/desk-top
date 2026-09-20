from typing import List, Dict, Any

def reciprocal_rank_fusion(
    vector_results: List[Dict[str, Any]],
    bm25_results: List[Dict[str, Any]],
    k: int = 60,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Reciprocal Rank Fusion (RRF) algorithm to combine vector and BM25 rankings.
    Formula: RRF(d) = sum(1 / (k + rank(d)))
    """
    scores: Dict[str, float] = {}
    doc_map: Dict[str, Dict[str, Any]] = {}

    # Process vector results
    for rank, item in enumerate(vector_results):
        content = item["content"]
        doc_map[content] = item
        scores[content] = scores.get(content, 0.0) + (1.0 / (k + rank + 1))

    # Process BM25 results
    for rank, item in enumerate(bm25_results):
        content = item["content"]
        if content not in doc_map:
            doc_map[content] = item
        scores[content] = scores.get(content, 0.0) + (1.0 / (k + rank + 1))

    # Compile fused list
    fused_items = []
    for content, score in scores.items():
        doc = doc_map[content]
        fused_items.append({
            "content": content,
            "metadata": doc.get("metadata", {}),
            "rrf_score": score,
            "vector_score": doc.get("vector_score", 0.0),
            "bm25_score": doc.get("bm25_score", 0.0)
        })

    fused_items.sort(key=lambda x: x["rrf_score"], reverse=True)
    return fused_items[:top_k]
