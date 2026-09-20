import os
import json
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks
from typing import List, Dict, Any
from backend.app.models.schema import IngestAuditItem, UnansweredQueryItem
from backend.app.core.config import settings

router = APIRouter()

UNANSWERED_FILE = os.path.join(settings.DATA_DIR, "storage", "unanswered_questions.json")

# Injected indexer reference
_indexer = None

def set_indexer(indexer):
    global _indexer
    _indexer = indexer

@router.get("/admin/unanswered", response_model=List[UnansweredQueryItem])
async def get_unanswered_questions():
    """List frequently asked queries that triggered controlled fallback."""
    if os.path.exists(UNANSWERED_FILE):
        try:
            with open(UNANSWERED_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    # Seed default sample unanswered insights
    return [
        UnansweredQueryItem(query="What is the 2026 hostel mess fee?", frequency=14, last_asked_at="2026-09-19T14:20:00"),
        UnansweredQueryItem(query="What is the 3rd semester ECE timetable?", frequency=9, last_asked_at="2026-09-18T11:15:00"),
        UnansweredQueryItem(query="How to apply for sports quota bus concession?", frequency=5, last_asked_at="2026-09-17T09:40:00")
    ]

@router.post("/admin/reindex")
async def trigger_reindex(crawl_live: bool = False):
    """Trigger document re-indexing from seed files or live website crawl."""
    if not _indexer:
        return {"status": "error", "message": "Indexer not initialized."}
    
    audit = await _indexer.run_full_ingestion(crawl_live=crawl_live)
    return {
        "status": "success",
        "message": "Re-indexing run completed successfully.",
        "audit": audit
    }

@router.get("/admin/audits")
async def get_ingestion_audits():
    """Retrieve history of crawler and ingestion runs."""
    if _indexer:
        return _indexer.get_latest_audits()
    return []
