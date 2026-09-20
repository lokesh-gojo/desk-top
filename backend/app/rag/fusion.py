from typing import List, Dict, Any

def get_chunk_id(item: Dict[str, Any]) -> str:
    """Generate or retrieve a unique, stable chunk identifier."""
    meta = item.get("metadata", {})
    if "chunk_id" in meta and meta["chunk_id"]:
        return str(meta["chunk_id"])
    doc_id = meta.get("document_id", "doc")
    idx = meta.get("chunk_index", 0)
    version = meta.get("version", 1)
    return f"{doc_id}_v{version}_c{idx}"

def reciprocal_rank_fusion(
    vector_results: List[Dict[str, Any]],
    bm25_results: List[Dict[str, Any]],
    k: int = 60,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Reciprocal Rank Fusion (RRF) algorithm to combine vector and BM25 rankings.
    Uses stable chunk_id (document_id + version + chunk_index) rather than
    raw text content as the dictionary key to prevent collision of identical text blocks.
    """
    scores: Dict[str, float] = {}
    doc_map: Dict[str, Dict[str, Any]] = {}

    # Process vector results
    for rank, item in enumerate(vector_results):
        cid = get_chunk_id(item)
        doc_map[cid] = item
        scores[cid] = scores.get(cid, 0.0) + (1.0 / (k + rank + 1))

    # Process BM25 results
    for rank, item in enumerate(bm25_results):
        cid = get_chunk_id(item)
        if cid not in doc_map:
            doc_map[cid] = item
        scores[cid] = scores.get(cid, 0.0) + (1.0 / (k + rank + 1))

    # Compile fused list
    fused_items = []
    for cid, score in scores.items():
        doc = doc_map[cid]
        doc_copy = dict(doc)
        doc_copy["rrf_score"] = score
        fused_items.append(doc_copy)

    fused_items.sort(key=lambda x: x["rrf_score"], reverse=True)
    return fused_items[:top_k]
