import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.rag.embeddings import EmbeddingService
from backend.app.rag.vector_search import VectorSearchEngine
from backend.app.rag.bm25_search import BM25SearchEngine
from backend.app.rag.pipeline import RAGPipeline
from backend.app.ingestion.indexer import DocumentIndexer

from backend.app.api.chat import router as chat_router, set_pipeline
from backend.app.api.notices import router as notices_router
from backend.app.api.feedback import router as feedback_router
from backend.app.api.admin import router as admin_router, set_indexer

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}...")
    
    # 1. Initialize RAG components
    embedder = EmbeddingService()
    vector_engine = VectorSearchEngine(embedding_service=embedder)
    bm25_engine = BM25SearchEngine()
    
    # 2. Ingest and index verified seed knowledge
    indexer = DocumentIndexer(vector_store=vector_engine)
    logger.info("Indexing verified EASA College seed knowledge...")
    seed_docs = indexer.load_seed_knowledge()
    
    # Chunk and populate both vector store and BM25 index
    from backend.app.ingestion.chunker import chunk_text
    all_chunks = []
    for doc in seed_docs:
        meta = {
            "document_id": doc.get("id"),
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
    logger.info(f"Successfully loaded {len(all_chunks)} semantic chunks into hybrid search engines.")

    # 3. Assemble RAG pipeline
    pipeline = RAGPipeline(vector_engine=vector_engine, bm25_engine=bm25_engine)
    set_pipeline(pipeline)
    set_indexer(indexer)

    yield
    logger.info("Shutting down EASA DeskBot backend.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# Enable CORS for frontend and cloud access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(chat_router, prefix=settings.API_PREFIX, tags=["Chat"])
app.include_router(notices_router, prefix=settings.API_PREFIX, tags=["Notices"])
app.include_router(feedback_router, prefix=settings.API_PREFIX, tags=["Feedback"])
app.include_router(admin_router, prefix=settings.API_PREFIX, tags=["Admin"])

@app.get("/health")
async def healthcheck():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "llm_provider": settings.LLM_PROVIDER
    }

# Mount frontend directory if present
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
