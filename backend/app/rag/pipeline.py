from typing import Dict, Any, List
from backend.app.core.logging import logger
from backend.app.core.security import sanitize_input, check_security_guardrails
from backend.app.core.config import settings
from backend.app.rag.vector_search import VectorSearchEngine
from backend.app.rag.bm25_search import BM25SearchEngine
from backend.app.rag.fusion import reciprocal_rank_fusion
from backend.app.rag.reranker import CrossFeatureReranker
from backend.app.rag.confidence import EvidenceConfidenceGate
from backend.app.prompts.system_prompt import build_rag_prompt, FALLBACK_ENGLISH, FALLBACK_TAMIL
from backend.app.llm.gemini import GeminiProvider
from backend.app.llm.openai import OpenAIProvider
from backend.app.llm.ollama import OllamaProvider
from backend.app.models.schema import ChatResponse, SourceCitation, EvidenceConfidence

class RAGPipeline:
    """
    Complete Strict Source-Grounded RAG pipeline for EASA College Helpdesk.
    """
    def __init__(self, vector_engine: VectorSearchEngine = None, bm25_engine: BM25SearchEngine = None):
        self.vector_engine = vector_engine or VectorSearchEngine()
        self.bm25_engine = bm25_engine or BM25SearchEngine()
        self.reranker = CrossFeatureReranker()
        self.confidence_gate = EvidenceConfidenceGate()
        
        # Initialize LLM
        if settings.LLM_PROVIDER == "openai":
            self.llm = OpenAIProvider()
        elif settings.LLM_PROVIDER == "ollama":
            self.llm = OllamaProvider()
        else:
            self.llm = GeminiProvider()

    async def answer_query(self, query: str, language: str = "en") -> ChatResponse:
        clean_q = sanitize_input(query)
        fallback_text = FALLBACK_TAMIL if language == "ta" else FALLBACK_ENGLISH

        # 1. Security guardrail check
        is_blocked, refusal_msg = check_security_guardrails(clean_q)
        if is_blocked:
            return ChatResponse(
                answer=refusal_msg,
                grounded=False,
                confidence=EvidenceConfidence(evidence_level="insufficient", grounded=False),
                sources=[],
                disclaimer="Personal student records and internal data are protected and excluded."
            )

        # 2. Hybrid Retrieval: Vector Search + BM25
        vector_results = self.vector_engine.search(clean_q, top_k=settings.MAX_RETRIEVAL_RESULTS)
        bm25_results = self.bm25_engine.search(clean_q, top_k=settings.MAX_RETRIEVAL_RESULTS)

        # 3. Reciprocal Rank Fusion
        fused = reciprocal_rank_fusion(vector_results, bm25_results, top_k=settings.MAX_RETRIEVAL_RESULTS)

        # 4. Multi-Feature Reranking (Authority, status, query coverage)
        reranked = self.reranker.rerank(clean_q, fused, top_k=4)

        # 5. Multi-Signal Evidence Confidence Gate
        is_confident, conf_summary = self.confidence_gate.evaluate(clean_q, reranked)

        # If evidence is insufficient, trigger controlled fallback directly without LLM
        if not is_confident or not reranked:
            logger.info(f"Query rejected by confidence gate: '{clean_q}' -> Fallback triggered.")
            return ChatResponse(
                answer=fallback_text,
                grounded=False,
                confidence=EvidenceConfidence(**conf_summary),
                sources=[],
                suggested_questions=[
                    "What UG courses are available?",
                    "What is the eligibility for B.E admission?",
                    "Does EASA bus go to Gandhipuram?",
                    "What hostel facilities are provided?"
                ],
                disclaimer="Strict grounding in effect: No matching verified records found in knowledge base."
            )

        # 6. Assemble Context & Citations
        context_blocks = []
        sources = []
        seen_urls = set()

        for chunk in reranked:
            content = chunk["content"]
            meta = chunk.get("metadata", {})
            title = meta.get("title", "EASA College Information")
            url = meta.get("canonical_url", "https://www.easacollege.com")
            verified_at = meta.get("last_verified", "2026-09-20")
            authority = meta.get("source_authority", "official_webpage")
            status = meta.get("status", "current")

            context_blocks.append(f"Document: {title} (Verified: {verified_at})\nContent: {content}")

            if url not in seen_urls:
                sources.append(SourceCitation(
                    title=title,
                    url=url,
                    category=meta.get("category", "general"),
                    verified_at=verified_at,
                    source_authority=authority,
                    status=status
                ))
                seen_urls.add(url)

        full_context = "\n\n".join(context_blocks)

        # 7. LLM Grounded Generation
        prompt = build_rag_prompt(clean_q, full_context, language=language)
        llm_answer = await self.llm.generate(prompt)

        # Suggested follow-up questions
        suggestions = self._generate_suggestions(reranked[0].get("metadata", {}).get("category", ""))

        return ChatResponse(
            answer=llm_answer,
            grounded=True,
            confidence=EvidenceConfidence(**conf_summary),
            sources=sources,
            suggested_questions=suggestions
        )

    def _generate_suggestions(self, category: str) -> List[str]:
        if category == "admission":
            return ["What is the TNEA code for EASA?", "What scholarships are offered?", "How to apply under management quota?"]
        elif category == "programmes":
            return ["What are the eligibility criteria for B.E?", "Does EASA offer CSE AI & ML?", "What PG courses are available?"]
        elif category == "hostel":
            return ["Are there separate hostels for boys and girls?", "What are the mess facilities?", "What sports facilities exist?"]
        elif category == "transport":
            return ["Does the bus go to Pollachi?", "Are there bus routes to Kerala?", "What is the Gandhipuram bus route?"]
        return ["What are the placement statistics?", "What facilities does the campus offer?", "How to contact the admission office?"]
