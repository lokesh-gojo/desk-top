import os
import time
from contextlib import asynccontextmanager
from typing import Dict
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.rag.embeddings import EmbeddingService
from backend.app.rag.vector_search import VectorSearchEngine
from backend.app.rag.bm25_search import BM25SearchEngine
from backend.app.rag.pipeline import RAGPipeline
from backend.app.ingestion.indexer import DocumentIndexer
from backend.app.db.storage import storage

from backend.app.api.chat import router as chat_router, set_pipeline
from backend.app.api.notices import router as notices_router
from backend.app.api.feedback import router as feedback_router
from backend.app.api.admin import router as admin_router, set_indexer

# Readiness tracker
_system_ready = False
_active_chunks_count = 0

# Simple sliding-window rate limiter per client IP (60 req / min)
RATE_LIMIT_WINDOW = 60.0  # seconds
MAX_REQUESTS_PER_WINDOW = 60
_rate_limit_records: Dict[str, list] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _system_ready, _active_chunks_count
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

    if chunks:
        if not vector_engine.chunks:
            vector_engine.add_chunks(chunks)
        bm25_engine.add_chunks(chunks)
        _active_chunks_count = len(chunks)
        logger.info(f"Ready: {_active_chunks_count} verified institutional chunks active.")

    # 3. Assemble RAG pipeline
    pipeline = RAGPipeline(vector_engine=vector_engine, bm25_engine=bm25_engine)
    set_pipeline(pipeline)
    set_indexer(indexer)

    _system_ready = True
    yield
    _system_ready = False
    logger.info("Shutting down EASA DeskBot backend.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# Rate Limiting & Payload Size Middleware
@app.middleware("http")
async def rate_limit_and_size_guard(request: Request, call_next):
    # Check payload size
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 100 * 1024:  # 100KB limit
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"detail": "Payload Too Large: Maximum request size is 100KB."}
        )

    # Rate limiting on API paths
    if request.url.path.startswith("/api/chat"):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        timestamps = _rate_limit_records.get(client_ip, [])
        # Purge timestamps outside the window
        valid_timestamps = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
        
        if len(valid_timestamps) >= MAX_REQUESTS_PER_WINDOW:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded: Maximum 60 requests per minute allowed."}
            )
        valid_timestamps.append(now)
        _rate_limit_records[client_ip] = valid_timestamps

    response = await call_next(request)
    return response

# Enable CORS with configurable origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# API Routers
app.include_router(chat_router, prefix=settings.API_PREFIX, tags=["Chat"])
app.include_router(notices_router, prefix=settings.API_PREFIX, tags=["Notices"])
app.include_router(feedback_router, prefix=settings.API_PREFIX, tags=["Feedback"])
app.include_router(admin_router, prefix=settings.API_PREFIX, tags=["Admin"])

# Liveness Probe
@app.get("/health")
async def healthcheck():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "llm_provider": settings.LLM_PROVIDER
    }

# Readiness Probe (Checks vector store readiness & database connectivity)
@app.get("/ready")
async def readiness_probe():
    if not _system_ready or _active_chunks_count == 0:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System initializing: Vector indices or persistent storage not yet ready."
        )
    return {
        "status": "ready",
        "service": settings.PROJECT_NAME,
        "active_chunks": _active_chunks_count,
        "embedding_model": settings.EMBEDDING_MODEL_NAME,
        "vector_dimension": settings.VECTOR_DIMENSION,
        "database": "Supabase" if settings.USE_SUPABASE else "Persistent SQLite"
    }

# Mount static frontend
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
