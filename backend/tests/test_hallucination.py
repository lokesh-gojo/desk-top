import pytest
import asyncio
from backend.app.rag.vector_search import VectorSearchEngine
from backend.app.rag.bm25_search import BM25SearchEngine
from backend.app.rag.pipeline import RAGPipeline
from backend.app.ingestion.indexer import DocumentIndexer
from backend.app.ingestion.chunker import chunk_text

@pytest.fixture(scope="module")
def setup_pipeline():
    vector_engine = VectorSearchEngine()
    bm25_engine = BM25SearchEngine()
    indexer = DocumentIndexer()
    seed_docs = indexer.load_seed_knowledge()
    
    all_chunks = []
    for doc in seed_docs:
        meta = {
            "title": doc.get("title"),
            "category": doc.get("category"),
            "canonical_url": doc.get("canonical_url"),
            "source_authority": doc.get("source_authority", "official_webpage"),
            "status": doc.get("status", "current"),
            "priority": doc.get("priority", 10),
            "last_verified": doc.get("last_verified", "2026-09-20")
        }
        chunks = chunk_text(doc.get("content", ""), meta)
        all_chunks.extend(chunks)

    vector_engine.add_chunks(all_chunks)
    bm25_engine.add_chunks(all_chunks)
    return RAGPipeline(vector_engine=vector_engine, bm25_engine=bm25_engine)

@pytest.mark.asyncio
async def test_unverified_hostel_fee_fallback(setup_pipeline):
    pipeline = setup_pipeline
    res = await pipeline.answer_query("What is the current CSE hostel fee for 2026-27?")
    # Must NOT invent arbitrary rupee amounts (e.g. 50,000 or 80,000)
    # Must trigger controlled fallback directing to office
    assert "couldn't find verified information" in res.answer.lower() or "contact" in res.answer.lower()
    assert res.confidence.grounded is False or res.confidence.evidence_level != "strong"

@pytest.mark.asyncio
async def test_timetable_fallback(setup_pipeline):
    pipeline = setup_pipeline
    res = await pipeline.answer_query("What is today's CSE 3rd semester timetable?")
    assert "couldn't find verified information" in res.answer.lower() or "contact" in res.answer.lower()

@pytest.mark.asyncio
async def test_unverified_staff_fallback(setup_pipeline):
    pipeline = setup_pipeline
    res = await pipeline.answer_query("Who is the current transport manager phone number?")
    assert "couldn't find verified information" in res.answer.lower() or "contact" in res.answer.lower()
