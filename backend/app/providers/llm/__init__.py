from typing import Optional
from app.core.config import settings
from app.providers.llm.base import LLMProvider
from app.providers.llm.gemini_provider import GeminiProvider
from app.providers.llm.openai_provider import OpenAICompatibleProvider
from app.providers.llm.mock_provider import MockLLMProvider

def get_llm_provider(
    provider_name: Optional[str] = None,
    tier: str = "fast",
    api_key: Optional[str] = None
) -> LLMProvider:
    """
    Factory function returning the configured LLMProvider.
    Tier can be 'fast' (for planning, scraping, extraction) or 'reasoning' (for verification, report synthesis).
    Supports dynamic user-provided API keys.
    """
    p_name = (provider_name or settings.DEFAULT_LLM_PROVIDER).lower()
    
    if p_name == "gemini":
        model = settings.REASONING_LLM_MODEL if tier == "reasoning" else settings.FAST_LLM_MODEL
        key = api_key or settings.GEMINI_API_KEY
        if key:
            return GeminiProvider(api_key=key, model=model)
        return MockLLMProvider()

    elif p_name in ("openai", "deepseek"):
        model = settings.OPENAI_MODEL or ("gpt-4o" if tier == "reasoning" else "gpt-4o-mini")
        if p_name == "deepseek":
            model = "deepseek-chat"
        key = api_key or settings.OPENAI_API_KEY or settings.DEEPSEEK_API_KEY
        if key:
            return OpenAICompatibleProvider(api_key=key, model=model)
        return MockLLMProvider()

    elif p_name == "mock":
        return MockLLMProvider()

    # Default fallback
    if api_key or settings.GEMINI_API_KEY:
        return GeminiProvider(api_key=api_key or settings.GEMINI_API_KEY)
    elif settings.OPENAI_API_KEY:
        return OpenAICompatibleProvider()
    return MockLLMProvider()
