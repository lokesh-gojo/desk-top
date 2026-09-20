import math
import re
from typing import List, Dict, Any

class BM25SearchEngine:
    """
    Keyword / Exact-Term search engine for EASA DeskBot.
    Essential for acronyms ('ECE', 'CSE-AIML', 'TNEA 2755', 'NAAC A')
    and exact locations ('Gandhipuram', 'Pollachi').
    """
    def __init__(self):
        self.corpus: List[Dict[str, Any]] = []
        self.tokenized_corpus: List[List[str]] = []
        self.doc_freqs: Dict[str, int] = {}
        self.avg_doc_len: float = 0.0
        self.k1 = 1.5
        self.b = 0.75

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        self.corpus.extend(chunks)
        for chunk in chunks:
            tokens = self._tokenize(chunk["content"])
            self.tokenized_corpus.append(tokens)
            
            # Count document frequencies
            unique_tokens = set(tokens)
            for tok in unique_tokens:
                self.doc_freqs[tok] = self.doc_freqs.get(tok, 0) + 1

        total_len = sum(len(t) for t in self.tokenized_corpus)
        self.avg_doc_len = total_len / len(self.tokenized_corpus) if self.tokenized_corpus else 1.0

    def search(self, query: str, top_k: int = 5, filter_status: str = "current") -> List[Dict[str, Any]]:
        if not self.corpus:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores = []
        n_docs = len(self.corpus)

        for idx, tokens in enumerate(self.tokenized_corpus):
            chunk = self.corpus[idx]
            meta = chunk.get("metadata", {})
            if filter_status and meta.get("status") != filter_status:
                continue

            doc_len = len(tokens)
            score = 0.0
            term_counts = {}
            for t in tokens:
                term_counts[t] = term_counts.get(t, 0) + 1

            for q_term in query_tokens:
                if q_term in self.doc_freqs:
                    df = self.doc_freqs[q_term]
                    idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)
                    tf = term_counts.get(q_term, 0)
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_doc_len))
                    score += idf * (numerator / denominator)

            if score > 0:
                scores.append({
                    "content": chunk["content"],
                    "metadata": meta,
                    "bm25_score": float(score)
                })

        scores.sort(key=lambda x: x["bm25_score"], reverse=True)
        # Normalize top score to 0.0 - 1.0 scale
        if scores:
            max_score = scores[0]["bm25_score"]
            if max_score > 0:
                for item in scores:
                    item["bm25_norm_score"] = min(1.0, item["bm25_score"] / max_score)
        return scores[:top_k]

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [t for t in re.findall(r"\b[a-zA-Z0-9_\-\&]+\b", text.lower()) if len(t) > 1]
