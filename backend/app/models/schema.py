from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import date

class Message(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    language: str = Field("en", description="'en' for English, 'ta' for Tamil")
    session_id: Optional[str] = None
    history: List[Message] = Field(default_factory=list)

class SourceCitation(BaseModel):
    title: str
    url: str
    category: str = "general"
    verified_at: str = "2026-09-20"
    source_authority: str = "official_webpage"
    status: str = "current"

class EvidenceConfidence(BaseModel):
    vector_score: float = 0.0
    bm25_score: float = 0.0
    rerank_score: float = 0.0
    overall_confidence: float = 0.0
    evidence_level: str = "strong"  # "strong", "moderate", "insufficient"
    source_authority: str = "official_webpage"
    status: str = "current"
    grounded: bool = True

class ChatResponse(BaseModel):
    answer: str
    grounded: bool
    confidence: EvidenceConfidence
    sources: List[SourceCitation] = Field(default_factory=list)
    suggested_questions: List[str] = Field(default_factory=list)
    disclaimer: Optional[str] = None

class FeedbackRequest(BaseModel):
    session_id: Optional[str] = None
    question: str
    answer: str
    rating: str = Field(..., description="'helpful' or 'unhelpful'")
    feedback_text: Optional[str] = None
    sources_cited: Optional[List[Dict[str, Any]]] = None

class NoticeItem(BaseModel):
    id: str
    title: str
    category: str
    content: str
    published_date: str
    expiry_date: Optional[str] = None
    status: str = "active"
    source_url: Optional[str] = None

class IngestAuditItem(BaseModel):
    run_id: str
    started_at: str
    completed_at: Optional[str] = None
    status: str
    pages_scanned: int
    new_documents: int
    updated_documents: int
    archived_documents: int
    chunks_generated: int
    embeddings_generated: int
    error_count: int
    summary_notes: Optional[str] = None

class UnansweredQueryItem(BaseModel):
    query: str
    frequency: int
    last_asked_at: str
    resolved: bool = False
