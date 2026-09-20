from fastapi import APIRouter, Depends
from typing import List
from backend.app.models.schema import NoticeItem
from backend.app.db.storage import storage
from backend.app.core.security import verify_admin_access

router = APIRouter()

@router.get("/notices", response_model=List[NoticeItem])
async def get_active_notices():
    """Retrieve all active dynamic college announcements from persistent storage."""
    return storage.get_active_notices()

@router.post("/notices", response_model=NoticeItem, dependencies=[Depends(verify_admin_access)])
async def create_notice(notice: NoticeItem):
    """
    Publish a new dynamic institutional notice (Admin RBAC Protected).
    Persists across server restarts.
    """
    return storage.add_notice(notice)
