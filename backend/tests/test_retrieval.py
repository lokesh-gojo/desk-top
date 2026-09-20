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
async def test_ug_courses_retrieval(setup_pipeline):
    pipeline = setup_pipeline
    res = await pipeline.answer_query("What UG courses are available?")
    assert res.grounded is True
    assert "Computer Science" in res.answer or "B.E" in res.answer or "B.Tech" in res.answer
    assert any("undergraduate-courses" in s.url for s in res.sources)

@pytest.mark.asyncio
async def test_acronym_ece_retrieval(setup_pipeline):
    pipeline = setup_pipeline
    res = await pipeline.answer_query("Tell me about ECE department and labs")
    assert res.grounded is True
    assert "Electronics and Communication" in res.answer or "VLSI" in res.answer or "ECE" in res.answer

@pytest.mark.asyncio
async def test_gandhipuram_bus_retrieval(setup_pipeline):
    pipeline = setup_pipeline
    res = await pipeline.answer_query("Does EASA bus go to Gandhipuram?")
    assert res.grounded is True
    assert "Gandhipuram" in res.answer
    assert any(s.category == "transport" for s in res.sources)

@pytest.mark.asyncio
async def test_hostel_capacity_retrieval(setup_pipeline):
    pipeline = setup_pipeline
    res = await pipeline.answer_query("What is the hostel boys capacity?")
    assert res.grounded is True
    assert "250" in res.answer or "Boys" in res.answer
