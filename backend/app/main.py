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
    
    # 2. Connect to persistent knowledge base
    indexer = DocumentIndexer(vector_store=vector_engine)
    chunks = indexer.load_cached_chunks()
    
    if not chunks:
        logger.info("No cached index found. Performing initial verified ingestion...")
        await indexer.run_full_ingestion(crawl_live=False)
        chunks = indexer.load_cached_chunks()

    # Populate in-memory BM25 index and vector cache
    if chunks:
        if not vector_engine.chunks:
            vector_engine.add_chunks(chunks)
        bm25_engine.add_chunks(chunks)
        logger.info(f"Ready: {len(chunks)} verified institutional chunks active.")

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
        "embedding_model": settings.EMBEDDING_MODEL_NAME,
        "vector_dimension": settings.VECTOR_DIMENSION,
        "llm_provider": settings.LLM_PROVIDER
    }

# Mount static frontend
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
