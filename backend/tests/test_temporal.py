import pytest
import asyncio
from backend.app.rag.vector_search import VectorSearchEngine
from backend.app.rag.bm25_search import BM25SearchEngine
from backend.app.rag.pipeline import RAGPipeline
from backend.app.ingestion.indexer import DocumentIndexer
from backend.app.ingestion.chunker import chunk_text

@pytest.fixture(scope="module")
def setup_pipeline_with_temporal():
    vector_engine = VectorSearchEngine()
    bm25_engine = BM25SearchEngine()
    
    # Add an archived historical chunk and a current 2026-27 chunk
    archived_chunk = {
        "content": "Old 2018 Admission Rule: Minimum qualifying cutoff for B.E was 50% for all categories and counselling was held in Chennai.",
        "metadata": {
            "title": "Archived Admission 2018",
            "category": "admission",
            "status": "archived",
            "priority": 2,
            "source_authority": "official_archived",
            "last_verified": "2018-05-10"
        }
    }
    
    current_chunk = {
        "content": "ADMISSION OPEN FOR ACADEMIC YEAR 2026-27: Higher Secondary (HSC 10+2) with Maths, Physics, Chemistry. Minimum marks 45% for General, 40% for BC/MBC/SC/ST. TNEA Code 2755.",
        "metadata": {
            "title": "UG Admission 2026-27 & Eligibility",
            "category": "admission",
            "status": "current",
            "priority": 10,
            "source_authority": "official_notice",
            "last_verified": "2026-09-20"
        }
    }
    
    vector_engine.add_chunks([archived_chunk, current_chunk])
    bm25_engine.add_chunks([archived_chunk, current_chunk])
    return RAGPipeline(vector_engine=vector_engine, bm25_engine=bm25_engine)

@pytest.mark.asyncio
async def test_temporal_prefers_current_admission(setup_pipeline_with_temporal):
    pipeline = setup_pipeline_with_temporal
    res = await pipeline.answer_query("What is the current admission eligibility?")
    
    # Must retrieve current 2026-27 source
    assert res.grounded is True
    assert any(s.status == "current" for s in res.sources)
    assert not any(s.status == "archived" for s in res.sources)
    assert "2026" in res.answer or "45%" in res.answer
