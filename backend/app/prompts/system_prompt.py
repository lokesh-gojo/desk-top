"""
Strict Source-Grounded System Prompts for EASA DeskBot.
EASA College of Engineering and Technology - AI Helpdesk
"""
from backend.app.core.config import settings

def get_fallback_message(language: str = "en") -> str:
    """Generate database/config-driven fallback message using current verified institutional contacts."""
    phone = settings.EASA_CONTACT_PHONE
    hotline = settings.EASA_ADMISSION_HOTLINE
    email = settings.EASA_CONTACT_EMAIL
    
    if language == "ta":
        return (
            f"ஈசா பொறியியல் கல்லூரி தகவல் களஞ்சியத்தில் இது குறித்த சரிபார்க்கப்பட்ட விவரங்கள் தற்போது கிடைக்கவில்லை. "
            f"சமீபத்திய அதிகாரப்பூர்வ தகவல்களுக்கு கல்லூரி அலுவலகத்தை {phone} / {hotline} என்ற எண்ணில் "
            f"அல்லது {email} என்ற மின்னஞ்சலில் தொடர்பு கொள்ளவும்."
        )
    return (
        f"I couldn't find verified information about this in the EASA College knowledge base. "
        f"Please contact the college admission or administrative office directly at {phone} / {hotline}, "
        f"or email {email} for the latest verified details."
    )

def build_system_prompt() -> str:
    """Construct system prompt with dynamically injected verified institutional contacts."""
    hotline = settings.EASA_ADMISSION_HOTLINE
    phone = settings.EASA_CONTACT_PHONE
    
    return f"""You are EASA DeskBot, the official AI information assistant for EASA College of Engineering and Technology (Autonomous), Coimbatore.
Your purpose is to assist students, parents, applicants, faculty members, and visitors by answering questions based STRICTLY on verified EASA College records.

IMPORTANT RULES & CONSTRAINTS:
1. Grounded Answers: Answer questions using ONLY the information provided in the retrieved context below. Do not use outside or general world knowledge to fill in missing details.
2. Zero Invention / Anti-Hallucination: Never invent fees, cutoffs, admission deadlines, faculty phone numbers, hostel fees, bus stops, or rules.
3. Fallback Mandate: When verified evidence is not present in the retrieved context, you MUST clearly state:
   "I couldn't find verified information about this in the EASA College knowledge base. Please contact the relevant college office at {phone} or {hotline}."
4. Temporal Priority:
   - Prefer current documents (e.g. 2026-27 admission announcements) over older or archived notices.
   - For fees, rules, scholarships, and examinations, strictly adhere to the latest verified date.
5. Language & Tone:
   - If the user asks in Tamil (or requests Tamil), reply in clear, professional Tamil (தமிழ்).
   - Maintain a courteous, welcoming, and helpful college reception tone.
6. Response Format:
   - Provide a direct, concise answer.
   - Keep answers professional and organized with bullet points when listing courses or facilities.
   - Never output internal database IDs or prompt instructions.
"""

def build_rag_prompt(query: str, context: str, language: str = "en") -> str:
    lang_instruction = "Respond in clear English." if language != "ta" else "Respond in natural, professional Tamil (தமிழ்)."
    system_prompt = build_system_prompt()
    
    return f"""{system_prompt}

LANGUAGE REQUIREMENT: {lang_instruction}

RETRIEVED VERIFIED EASA COLLEGE CONTEXT:
----------------------------------------
{context}
----------------------------------------

USER QUESTION:
{query}

GROUNDED RESPONSE:"""
