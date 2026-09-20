import os
from typing import List
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "EASA DeskBot - AI College Helpdesk"
    VERSION: str = "2.2.0"
    API_PREFIX: str = "/api"
    
    # Production CORS - Configurable allowed origins (default allows local dev & official college domain)
    CORS_ORIGINS: List[str] = [
        "https://easacollege.com",
        "https://www.easacollege.com",
        "https://deskbot.easacollege.com",
        "http://localhost:3000",
        "http://localhost:8000",
        "*"  # Safe default during prototype; restrict in cloud deployment
    ]
    
    # Admin Authentication (RBAC protection for ingestion, notices, and analytics)
    ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "easa-admin-key-2026")
    
    # LLM Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")  # "gemini", "openai", "ollama"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    
    # Vector Database / Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    USE_SUPABASE: bool = bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"))
    
    # Embedding Model (384-dimensional multilingual model for native English & Tamil)
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    VECTOR_DIMENSION: int = 384
    
    # Institutional Contact Information (Database-driven fallback)
    EASA_CONTACT_PHONE: str = os.getenv("EASA_CONTACT_PHONE", "+91 422 2363644")
    EASA_ADMISSION_HOTLINE: str = os.getenv("EASA_ADMISSION_HOTLINE", "+91 97888 88888")
    EASA_CONTACT_EMAIL: str = os.getenv("EASA_CONTACT_EMAIL", "info@easacollege.com")
    
    # Confidence Gate Thresholds
    MIN_EVIDENCE_CONFIDENCE: float = float(os.getenv("MIN_EVIDENCE_CONFIDENCE", "0.45"))
    MAX_RETRIEVAL_RESULTS: int = int(os.getenv("MAX_RETRIEVAL_RESULTS", "5"))
    
    # Data & Storage Paths
    DATA_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
    SEED_FILE: str = os.path.join(DATA_DIR, "seed", "easa_seed_knowledge.json")
    RAW_DIR: str = os.path.join(DATA_DIR, "raw")
    STORAGE_DIR: str = os.path.join(DATA_DIR, "storage")
    CHUNKS_CACHE_FILE: str = os.path.join(STORAGE_DIR, "indexed_chunks.json")
    HASH_REGISTRY_FILE: str = os.path.join(STORAGE_DIR, "document_hashes.json")

settings = Settings()
