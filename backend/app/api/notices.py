from fastapi import APIRouter
from typing import List
from datetime import date
from backend.app.models.schema import NoticeItem

router = APIRouter()

# In-memory / storage notices
_NOTICES: List[NoticeItem] = [
    NoticeItem(
        id="notice-2026-001",
        title="B.E / B.Tech Admissions Open 2026-27",
        category="admission",
        content="Applications are officially invited for 2026-27 Bachelor of Engineering & Technology admissions. Merit scholarship interviews underway.",
        published_date="2026-03-01",
        expiry_date="2026-10-31",
        status="active",
        source_url="https://www.easacollege.com/undergraduate-courses-in-coimbatore"
    ),
    NoticeItem(
        id="notice-2026-002",
        title="Campus Placement Drive - IT & Core Sectors",
        category="placement",
        content="Final year and pre-final year students are notified of upcoming pooled campus placement drives scheduled for this semester.",
        published_date="2026-09-10",
        expiry_date="2026-11-15",
        status="active",
        source_url="https://www.easacollege.com/placement-training-team"
    ),
    NoticeItem(
        id="notice-2026-003",
        title="College Bus Routes Schedule - 2026-27",
        category="transport",
        content="Updated morning boarding times for Gandhipuram, Singanallur, Pollachi, and Kerala routes are active.",
        published_date="2026-08-20",
        expiry_date="2027-05-31",
        status="active",
        source_url="https://www.easacollege.com/life-at-easa-campus"
    )
]

@router.get("/notices", response_model=List[NoticeItem])
async def get_active_notices():
    """Retrieve all active dynamic college announcements."""
    today = date.today().isoformat()
    active = [n for n in _NOTICES if n.status == "active" and (not n.expiry_date or n.expiry_date >= today)]
    return active

@router.post("/notices", response_model=NoticeItem)
async def create_notice(notice: NoticeItem):
    """Add a new dynamic notice (Admin capability)."""
    _NOTICES.insert(0, notice)
    return notice
