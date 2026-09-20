import httpx
from backend.app.llm.base import LLMProvider
from backend.app.core.logging import logger
from backend.app.core.config import settings

class OllamaProvider(LLMProvider):
    """Local / Self-hosted Ollama provider (e.g. Llama 3, Mistral)."""
    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.model = model or settings.OLLAMA_MODEL

    async def generate(self, prompt: str, system_instruction: str = "") -> str:
        url = f"{self.base_url.rstrip('/')}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_instruction,
            "stream": False,
            "options": {"temperature": 0.2}
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    return resp.json().get("response", "").strip()
                logger.error(f"Ollama error {resp.status_code}: {resp.text}")
                return "Error connecting to local Ollama instance."
        except Exception as e:
            logger.warning(f"Ollama not running: {e}")
            return "Local Ollama server is unreachable."
