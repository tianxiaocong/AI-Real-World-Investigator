from abc import ABC, abstractmethod
from typing import Optional, Type, TypeVar, Any
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class LLMProvider(ABC):
    """Abstract Base Class for all LLM Providers"""

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate freeform raw text response"""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
    ) -> T:
        """Generate structured response strictly validated against a Pydantic Model"""
        pass
    
    @abstractmethod
    async def get_embedding(self, text: str) -> list[float]:
        """Generate vector embedding for a snippet/claim"""
        pass
