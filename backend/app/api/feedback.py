import os
import json
from fastapi import APIRouter
from typing import List
from backend.app.models.schema import FeedbackRequest
from backend.app.core.config import settings

router = APIRouter()

FEEDBACK_FILE = os.path.join(settings.DATA_DIR, "storage", "feedback_logs.json")

@router.post("/feedback")
async def submit_feedback(fb: FeedbackRequest):
    """Save thumbs up/down and user comments on DeskBot answers."""
    os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)
    records = []
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                records = json.load(f)
        except Exception:
            records = []
            
    records.append(fb.model_dump())
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(records[-200:], f, indent=2)
        
    return {"status": "success", "message": "Feedback recorded. Thank you for helping improve EASA DeskBot."}

@router.get("/feedback")
async def get_feedback():
    """Retrieve recorded feedback for admin review."""
    if os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []
