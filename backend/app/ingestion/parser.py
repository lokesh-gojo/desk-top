import hashlib
import re
from datetime import date
from typing import Dict, Any

def compute_content_hash(text: str) -> str:
    """Compute SHA-256 hash of text to detect document changes."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def infer_category(url: str, text: str) -> str:
    """Infer knowledge category from URL path and textual signals."""
    u = url.lower()
    t = text.lower()
    
    if "undergraduate" in u or "admission" in u or "tnea" in t or "admission open" in t:
        return "admission"
    elif "postgraduate" in u or "courses" in u or "curriculum" in t:
        return "programmes"
    elif "hostel" in u or "mess" in t:
        return "hostel"
    elif "bus" in u or "transport" in u or "route" in t:
        return "transport"
    elif "placement" in u or "recruit" in t or "training-team" in u:
        return "placements"
    elif "teaching-staff" in u or "faculty" in t or "department" in t:
        return "departments"
    elif "exam-cell" in u or "grievance" in u or "coe" in t:
        return "student_support"
    elif "campus" in u or "facility" in u or "library" in t:
        return "facilities"
    return "college_profile"

def extract_temporal_metadata(text: str) -> Dict[str, Any]:
    """Detect current vs archived signals (e.g. 2026-27 vs legacy 2017-2021)."""
    current_year = date.today().year
    
    is_current = False
    priority = 8
    status = "current"
    authority = "official_webpage"
    
    if "2026" in text or "2026-27" in text or "2026–27" in text or "admission open" in text.lower():
        is_current = True
        priority = 10
        status = "current"
        authority = "official_notice" if "admission open" in text.lower() else "official_webpage"
    elif any(yr in text for yr in ["2017", "2018", "2019", "2020", "2021"]):
        # Check if it doesn't mention current accreditation/autonomous status
        if "autonomous" not in text.lower():
            status = "archived"
            priority = 3
            authority = "official_archived"
            
    return {
        "status": status,
        "priority": priority,
        "source_authority": authority,
        "last_verified": date.today().isoformat(),
        "effective_from": f"{current_year}-01-01" if is_current else "2020-01-01",
        "effective_to": f"{current_year + 1}-05-31" if is_current else None
    }
