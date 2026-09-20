from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from backend.app.models.schema import IngestAuditItem, UnansweredQueryItem
from backend.app.db.storage import storage
from backend.app.core.security import verify_admin_access

router = APIRouter()

# Injected indexer reference
_indexer = None

def set_indexer(indexer):
    global _indexer
    _indexer = indexer

@router.get("/admin/unanswered", response_model=List[UnansweredQueryItem], dependencies=[Depends(verify_admin_access)])
async def get_unanswered_questions():
    """List frequently asked queries that triggered controlled fallback (Admin RBAC Protected)."""
    return storage.get_unanswered_queries()

@router.post("/admin/reindex", dependencies=[Depends(verify_admin_access)])
async def trigger_reindex(crawl_live: bool = False):
    """
    Trigger document re-indexing from seed files or live website crawl (Admin RBAC Protected).
    Uses SHA-256 hash checking to incrementally update only changed content.
    """
    if not _indexer:
        return {"status": "error", "message": "Indexer not initialized."}
    
    audit = await _indexer.run_full_ingestion(crawl_live=crawl_live)
    return {
        "status": "success",
        "message": "Incremental re-indexing run completed successfully.",
        "audit": audit
    }

@router.get("/admin/audits", dependencies=[Depends(verify_admin_access)])
async def get_ingestion_audits():
    """Retrieve history of crawler and ingestion runs (Admin RBAC Protected)."""
    if _indexer:
        return _indexer.get_latest_audits()
    return []
