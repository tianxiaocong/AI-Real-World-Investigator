import asyncio
import logging
from typing import List
from duckduckgo_search import DDGS
from app.providers.search.base import SearchProvider, SearchResultItem

logger = logging.getLogger(__name__)

class DuckDuckGoProvider(SearchProvider):
    """DuckDuckGo Free Search Provider with region fallback and retry"""

    async def search(self, query: str, max_results: int = 5) -> List[SearchResultItem]:
        def _sync_search():
            results = []
            # Try global region first, then cn-zh for Chinese queries
            regions = ["wt-wt"]
            if any("\u4e00" <= ch <= "\u9fff" for ch in query):
                regions = ["cn-zh", "wt-wt"]

            for reg in regions:
                try:
                    with DDGS() as ddgs:
                        raw_results = list(ddgs.text(query, region=reg, max_results=max_results, safesearch="moderate"))
                        if raw_results:
                            for item in raw_results:
                                u = item.get("href") or item.get("link") or ""
                                t = item.get("title") or ""
                                b = item.get("body") or item.get("snippet") or ""
                                if u and t:
                                    results.append(
                                        SearchResultItem(
                                            title=t,
                                            url=u,
                                            snippet=b
                                        )
                                    )
                            if results:
                                break
                except Exception as e:
                    logger.warning(f"DuckDuckGo search error (region={reg}) for '{query}': {e}")
            return results

        return await asyncio.to_thread(_sync_search)
