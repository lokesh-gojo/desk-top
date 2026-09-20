import os
from typing import List
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "EASA DeskBot - AI College Helpdesk"
    VERSION: str = "2.0.0"
    API_PREFIX: str = "/api"
    
    # Allowed CORS Origins
    CORS_ORIGINS: List[str] = ["*"]
    
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
    
    # Embedding Model (384-dim default for fast local / BGE-M3 multilingual)
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
    
    # Confidence Gate Thresholds
    MIN_EVIDENCE_CONFIDENCE: float = float(os.getenv("MIN_EVIDENCE_CONFIDENCE", "0.45"))
    MAX_RETRIEVAL_RESULTS: int = int(os.getenv("MAX_RETRIEVAL_RESULTS", "5"))
    
    # Data Paths
    DATA_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
    SEED_FILE: str = os.path.join(DATA_DIR, "seed", "easa_seed_knowledge.json")
    RAW_DIR: str = os.path.join(DATA_DIR, "raw")
    STORAGE_DIR: str = os.path.join(DATA_DIR, "storage")

settings = Settings()
