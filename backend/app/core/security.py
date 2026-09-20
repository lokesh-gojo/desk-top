import re
from typing import Tuple

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"system\s+prompt",
    r"developer\s+mode",
    r"jailbreak",
    r"reveal\s+(internal|database|password|secret|key)",
    r"sql\s+injection",
    r"give\s+me\s+private\s+student",
    r"student\s+(marks|attendance|password|phone\s+number)"
]

def sanitize_input(text: str) -> str:
    """Strip dangerous characters and trim whitespace."""
    if not text:
        return ""
    # Strip non-printable or suspicious control characters
    cleaned = "".join(ch for ch in text if ch.isprintable())
    return cleaned.strip()[:1000]

def check_security_guardrails(query: str) -> Tuple[bool, str]:
    """
    Check if query attempts prompt injection or requests private/restricted records.
    Returns: (is_blocked, refusal_reason)
    """
    lower = query.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lower):
            if "private student" in lower or "marks" in lower or "attendance" in lower:
                return True, "Personal student records, attendance, and internal marks are not part of the public helpdesk. Please log in to the official EASA student ERP portal or contact the college office directly."
            return True, "I am EASA DeskBot, the official college assistant. I only provide verified public information regarding EASA College of Engineering and Technology."
    
    return False, ""
