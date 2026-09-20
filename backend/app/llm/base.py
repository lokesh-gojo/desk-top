from abc import ABC, abstractmethod

class LLMProvider(ABC):
    """Abstract base class for pluggable LLM inference."""
    
    @abstractmethod
    async def generate(self, prompt: str, system_instruction: str = "") -> str:
        """Generate grounded text response given prompt and system instructions."""
        pass
