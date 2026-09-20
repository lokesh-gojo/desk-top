import httpx
from backend.app.llm.base import LLMProvider
from backend.app.core.logging import logger
from backend.app.core.config import settings

class OpenAIProvider(LLMProvider):
    """OpenAI API provider for GPT models."""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL

    async def generate(self, prompt: str, system_instruction: str = "") -> str:
        if not self.api_key:
            return "OpenAI API Key not configured."
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction or "You are EASA DeskBot. Answer strictly from context."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"].strip()
                logger.error(f"OpenAI error {resp.status_code}: {resp.text}")
                return "Error connecting to OpenAI."
        except Exception as e:
            logger.error(f"OpenAI connection error: {e}")
            return "Failed to reach OpenAI service."
