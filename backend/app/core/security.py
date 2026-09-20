import re
from typing import Tuple, Optional
from fastapi import Header, HTTPException, status
from backend.app.core.config import settings

# Core regex patterns for early prompt-injection rejection
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"system\s+prompt",
    r"developer\s+mode",
    r"jailbreak",
    r"reveal\s+(internal|database|password|secret|key)",
    r"sql\s+injection",
    r"give\s+me\s+private\s+student",
    r"student\s+(marks|attendance|password|phone\s+number)",
    r"administrative\s+credentials",
    r"drop\s+table",
    r"union\s+select"
]

# Prohibited leakage patterns in model outputs
LEAKAGE_PATTERNS = [
    r"system\s*prompt\s*:",
    r"retrieved\s*verified\s*easa\s*college\s*context",
    r"grounded\s*response\s*:",
    r"supabase_key",
    r"gemini_api_key",
    r"admin_api_key",
    r"password\s*="
]

def sanitize_input(text: str) -> str:
    """Sanitize and normalize user input characters."""
    if not text:
        return ""
    cleaned = "".join(ch for ch in text if ch.isprintable() or ch in "\n\t")
    cleaned = re.sub(r"(\r\n|\r|\n){3,}", "\n\n", cleaned)
    cleaned = re.sub(r"(`{3,}|-{3,})", " ", cleaned)
    return cleaned.strip()[:1000]

def check_security_guardrails(query: str) -> Tuple[bool, str]:
    """
    Multi-layer security validator:
    - Checks input length & structural anomalies
    - Pattern-based prompt injection detection
    - ERP / Private student records refusal
    Returns: (is_blocked, refusal_reason)
    """
    if not query or len(query.strip()) < 2:
        return True, "Please enter a valid question regarding EASA College."
        
    lower = query.lower()

    if lower.count("system:") > 1 or lower.count("assistant:") > 1:
        return True, "Invalid query format. Please ask standard college-related questions."

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lower):
            if any(term in lower for term in ["private student", "marks", "attendance", "credential"]):
                return True, (
                    "Personal student records, attendance, internal marks, and administrative credentials "
                    "are strictly protected and excluded from the public helpdesk. Please access the authenticated "
                    "EASA College ERP portal or visit the Controller of Examinations."
                )
            return True, (
                "I am EASA DeskBot, the official college assistant. I only provide verified institutional "
                "information regarding EASA College of Engineering and Technology."
            )
    
    return False, ""

def validate_model_output(output_text: str, fallback_message: str) -> str:
    """
    Output guardrail validator:
    Ensures LLM response has not leaked internal prompts, database tokens, or instructions.
    """
    if not output_text:
        return fallback_message
        
    lower = output_text.lower()
    for leak in LEAKAGE_PATTERNS:
        if re.search(leak, lower):
            return fallback_message
            
    return output_text.strip()

def verify_admin_access(
    x_admin_api_key: Optional[str] = Header(None, alias="X-Admin-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    FastAPI dependency enforcing RBAC / Admin authentication for administrative endpoints.
    Accepts:
    1. Header 'X-Admin-API-Key: <ADMIN_API_KEY>'
    2. Header 'Authorization: Bearer <ADMIN_API_KEY>'
    """
    expected_key = settings.ADMIN_API_KEY
    provided_key = None

    if x_admin_api_key:
        provided_key = x_admin_api_key.strip()
    elif authorization and authorization.lower().startswith("bearer "):
        provided_key = authorization[7:].strip()

    if not provided_key or provided_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Valid X-Admin-API-Key or Bearer token required for administrative operations."
        )
    return True
