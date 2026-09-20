import re
from typing import List, Optional
from backend.app.models.schema import Message
from backend.app.core.logging import logger

ENTITY_PATTERNS = {
    "ece": "Electronics and Communication Engineering (ECE)",
    "cse": "Computer Science and Engineering (CSE)",
    "aiml": "CSE Artificial Intelligence and Machine Learning (AI & ML)",
    "cyber": "CSE Cyber Security",
    "biomedical": "Biomedical Engineering (BME)",
    "mech": "Mechanical Engineering",
    "eee": "Electrical and Electronics Engineering (EEE)",
    "agri": "Agricultural Engineering",
    "it": "Information Technology (IT)",
    "aids": "Artificial Intelligence and Data Science (AI & DS)",
    "mba": "Master of Business Administration (MBA)",
    "hostel": "Hostel facilities, rooms and accommodation",
    "transport": "College bus routes and transport",
    "placement": "Placements, recruiters and training"
}

def extract_last_referenced_entity(history: List[Message]) -> Optional[str]:
    """Scan recent dialogue history to extract the most recent institutional entity."""
    for msg in reversed(history):
        text = msg.content.lower()
        for key, full_name in ENTITY_PATTERNS.items():
            if re.search(r"\b" + re.escape(key) + r"\b", text):
                return full_name
    return None

def rewrite_conversational_query(query: str, history: List[Message]) -> str:
    """
    Contextual and entity-aware conversational query rewriter:
    Extracts referenced topics/courses from prior dialogue turns and binds them
    to anaphoric and elliptical queries ('What about that course?', 'Its fees?', 'How to apply?').
    """
    if not history:
        return query

    clean_q = query.strip()
    clean_q_lower = clean_q.lower()
    
    last_entity = extract_last_referenced_entity(history)

    # Check for pronoun / anaphoric references: "that course", "it", "its", "that department"
    is_anaphoric = any(p in clean_q_lower for p in [
        "that course", "that department", "about that", "for that",
        "its", "it", "their", "fees for that", "eligibility for that"
    ]) or len(clean_q.split()) <= 4

    if is_anaphoric and last_entity:
        rewritten = f"{last_entity} at EASA College - {clean_q}"
        logger.info(f"Entity-Aware Anaphoric Rewrite: '{query}' [Entity: {last_entity}] -> '{rewritten}'")
        return rewritten

    # Direct acronym expansions
    for key, full_name in ENTITY_PATTERNS.items():
        if re.search(r"\b" + re.escape(key) + r"\b", clean_q_lower):
            rewritten = f"{full_name} at EASA College - {clean_q}"
            logger.info(f"Entity Expansion Rewrite: '{query}' -> '{rewritten}'")
            return rewritten

    # Fallback to topic fusion with last user query
    last_user_turn = ""
    for msg in reversed(history):
        if msg.role == "user":
            last_user_turn = msg.content.strip()
            break

    if last_user_turn and len(clean_q.split()) <= 5:
        rewritten = f"{last_user_turn} - {clean_q}"
        logger.info(f"Conversational Context Fusion: '{query}' -> '{rewritten}'")
        return rewritten

    return query
