from typing import Optional
from app.core.config import settings
from app.providers.search.base import SearchProvider
from app.providers.search.duckduckgo_provider import DuckDuckGoProvider
from app.providers.search.tavily_provider import TavilySearchProvider
from app.providers.search.mock_provider import MockSearchProvider

def get_search_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None
) -> SearchProvider:
    """Factory function to get the requested search provider with optional custom API key"""
    p_name = (provider_name or settings.DEFAULT_SEARCH_PROVIDER).lower()
    tavily_key = api_key or settings.TAVILY_API_KEY
    
    if p_name == "tavily" and tavily_key:
        return TavilySearchProvider(api_key=tavily_key)
    elif p_name == "duckduckgo":
        return DuckDuckGoProvider()
    elif p_name == "mock":
        return MockSearchProvider()
        
    # Default fallback
    if tavily_key:
        return TavilySearchProvider(api_key=tavily_key)
    return DuckDuckGoProvider()
