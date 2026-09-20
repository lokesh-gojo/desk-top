import re
from typing import List
from backend.app.models.schema import Message
from backend.app.core.logging import logger

ANAPHORIC_PATTERNS = [
    r"^what\s+about\s+",
    r"^and\s+(for\s+)?",
    r"\b(it|its|their|that|this)\b",
    r"^tell\s+me\s+more",
    r"^does\s+it\s+",
    r"^is\s+it\s+",
    r"^how\s+much\s+",
    r"^fees?\s+for\s+that"
]

def is_conversational_followup(query: str, history: List[Message]) -> bool:
    """Determine if a query relies on previous conversational context."""
    if not history:
        return False
    q_lower = query.strip().lower()
    
    # Short elliptical queries (e.g. "What about ECE?", "Eligibility?")
    if len(q_lower.split()) <= 4:
        return True

    for pattern in ANAPHORIC_PATTERNS:
        if re.search(pattern, q_lower):
            return True
    return False

def rewrite_conversational_query(query: str, history: List[Message]) -> str:
    """
    Contextual query rewriter:
    Resolves conversational pronouns, ellipses, and follow-ups
    into a self-contained search query for the RAG retriever.
    
    Example:
    History: User asked "What UG courses are available?"
    Current: "What about ECE?"
    Rewritten: "What are the details, eligibility and courses for ECE (Electronics and Communication Engineering) at EASA College?"
    """
    if not is_conversational_followup(query, history):
        return query

    # Find the last relevant user query and assistant answer summary
    last_user_turn = ""
    for msg in reversed(history):
        if msg.role == "user":
            last_user_turn = msg.content.strip()
            break

    clean_q = query.strip()
    clean_q_lower = clean_q.lower()

    # Rule-based contextual expansions for common college follow-ups
    if re.search(r"\bece\b", clean_q_lower):
        rewritten = "Electronics and Communication Engineering ECE department courses laboratories and faculty details at EASA College"
    elif re.search(r"\bcse\b", clean_q_lower):
        rewritten = "Computer Science and Engineering CSE courses and AI ML Cyber Security at EASA College"
    elif re.search(r"\b(hostel|mess|rooms?)\b", clean_q_lower):
        rewritten = f"Hostel accommodation, rooms, facilities, and mess services at EASA College: {clean_q}"
    elif re.search(r"\b(bus|transport|route)\b", clean_q_lower):
        rewritten = f"College bus routes, boarding points, and transport at EASA College: {clean_q}"
    elif re.search(r"\b(fees?|cost|tuition)\b", clean_q_lower):
        rewritten = f"Admission tuition fees, scholarships, and fee waivers at EASA College: {clean_q}"
    elif last_user_turn:
        # Fuse current query with previous user topic
        rewritten = f"{last_user_turn} - {clean_q}"
    else:
        rewritten = f"EASA College {clean_q}"

    logger.info(f"Conversational Rewrite: '{query}' -> '{rewritten}'")
    return rewritten
