import os
import httpx
from backend.app.llm.base import LLMProvider
from backend.app.core.logging import logger
from backend.app.core.config import settings

class GeminiProvider(LLMProvider):
    """
    Gemini LLM Provider implementing Google's modern Generative AI client.
    Supports official google-genai SDK with resilient REST API fallback.
    """
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self.client = None
        
        # Try initializing google.genai Client if installed and key present
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                logger.info(f"GeminiProvider initialized with google-genai SDK ({self.model})")
            except ImportError:
                logger.warning("google-genai package not found. Using direct HTTP client fallback for Gemini.")
            except Exception as e:
                logger.warning(f"Failed to initialize google-genai Client: {e}. Falling back to REST.")

    async def generate(self, prompt: str, system_instruction: str = "") -> str:
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not configured. Returning rule-based grounded context summary.")
            return self._extract_grounded_fallback(prompt)

        # 1. Use official SDK if available
        if self.client:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.models.generate_content(
                        model=self.model,
                        contents=prompt,
                    )
                )
                if response and hasattr(response, "text") and response.text:
                    return response.text.strip()
            except Exception as e:
                logger.warning(f"google-genai SDK generation error: {e}. Attempting REST fallback.")

        # 2. Resilient REST API fallback
        return await self._generate_via_rest(prompt, system_instruction)

    async def _generate_via_rest(self, prompt: str, system_instruction: str = "") -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1024
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
                logger.error(f"Gemini REST error {resp.status_code}: {resp.text}")
                return self._extract_grounded_fallback(prompt)
        except Exception as e:
            logger.error(f"Gemini REST connection failure: {e}")
            return self._extract_grounded_fallback(prompt)

    def _extract_grounded_fallback(self, prompt: str) -> str:
        """When LLM API is unavailable, synthesize from retrieved context strictly."""
        if "RETRIEVED VERIFIED EASA COLLEGE CONTEXT:" in prompt:
            parts = prompt.split("RETRIEVED VERIFIED EASA COLLEGE CONTEXT:")
            if len(parts) > 1:
                context_chunk = parts[1].split("USER QUESTION:")[0].strip()
                # Return the clean facts directly without hallucination
                clean_lines = [l.strip() for l in context_chunk.split("\n") if l.strip() and not l.startswith("-") and not l.startswith("Source:")]
                if clean_lines:
                    return clean_lines[0]
        return "I couldn't find verified information about this in the EASA College knowledge base. Please contact the admission office at +91 97888 88888."
