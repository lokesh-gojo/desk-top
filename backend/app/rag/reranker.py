from typing import List, Dict, Any

AUTHORITY_WEIGHTS = {
    "official_notice": 1.25,
    "official_webpage": 1.15,
    "official_pdf": 1.05,
    "official_archived": 0.50,
    "unverified": 0.30
}

class CrossFeatureReranker:
    """
    Reranks fused hybrid candidates using multi-signal institutional scoring:
    - Source Authority hierarchy
    - Temporal validity & Priority
    - Exact query phrase coverage
    """
    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 4) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        query_words = set(w.lower() for w in query.split() if len(w) > 2)

        reranked = []
        for item in candidates:
            content = item["content"].lower()
            meta = item.get("metadata", {})
            
            # 1. Base scores from vector / fusion
            base_score = item.get("rrf_score", 0.0) * 100.0
            vector_score = item.get("vector_score", 0.0)
            
            # 2. Source authority multiplier
            authority = meta.get("source_authority", "official_webpage")
            auth_weight = AUTHORITY_WEIGHTS.get(authority, 1.0)
            
            # 3. Temporal status multiplier
            status = meta.get("status", "current")
            status_weight = 1.2 if status == "current" else 0.4
            
            # 4. Keyword phrase match boost
            matched_words = sum(1 for w in query_words if w in content)
            coverage_boost = (matched_words / max(len(query_words), 1)) * 0.35
            
            # 5. Exact match bonus for college specific terms
            exact_bonus = 0.0
            if "2026" in query and ("2026-27" in content or "2026" in content):
                exact_bonus += 0.25
            if any(acronym in query.upper().split() for acronym in ["ECE", "CSE", "EEE", "BME", "MBA", "TNEA", "NAAC"]):
                exact_bonus += 0.15

            final_score = (base_score * 0.4 + vector_score * 0.6 + coverage_boost + exact_bonus) * auth_weight * status_weight

            item_copy = dict(item)
            item_copy["rerank_score"] = float(round(final_score, 4))
            item_copy["source_authority"] = authority
            item_copy["status"] = status
            reranked.append(item_copy)

        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
        return reranked[:top_k]
