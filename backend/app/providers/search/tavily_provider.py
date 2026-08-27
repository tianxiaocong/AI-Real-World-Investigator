import logging
from typing import List, Optional
import httpx
from app.core.config import settings
from app.providers.search.base import SearchProvider, SearchResultItem

logger = logging.getLogger(__name__)

class TavilySearchProvider(SearchProvider):
    """Tavily Search Provider (AI-Optimized Search Engine)"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.TAVILY_API_KEY

    async def search(self, query: str, max_results: int = 5) -> List[SearchResultItem]:
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY is not configured.")

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "advanced",
            "max_results": max_results,
            "include_raw_content": False
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                results = []
                for item in data.get("results", []):
                    results.append(
                        SearchResultItem(
                            title=item.get("title", ""),
                            url=item.get("url", ""),
                            snippet=item.get("content", ""),
                            score=item.get("score")
                        )
                    )
                return results
            except Exception as e:
                logger.error(f"Tavily search failed: {e}")
                return []
