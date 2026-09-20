from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from backend.app.models.schema import FeedbackRequest
from backend.app.db.storage import storage
from backend.app.core.security import verify_admin_access

router = APIRouter()

@router.post("/feedback")
async def submit_feedback(fb: FeedbackRequest):
    """Save thumbs up/down and user comments on DeskBot answers into persistent storage."""
    fb_id = storage.save_feedback(fb)
    return {
        "status": "success",
        "feedback_id": fb_id,
        "message": "Feedback recorded in persistent storage. Thank you for helping improve EASA DeskBot."
    }

@router.get("/feedback", dependencies=[Depends(verify_admin_access)])
async def get_feedback():
    """Retrieve recorded feedback logs (Admin RBAC Protected)."""
    return storage.get_all_feedback()
