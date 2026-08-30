import asyncio
import logging
import base64
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
import httpx
from duckduckgo_search import DDGS
from app.providers.search.base import SearchProvider, SearchResultItem

logger = logging.getLogger(__name__)


def _decode_bing_url(href: str) -> str:
    """Decode real URL from Bing redirect link: &u=a1<base64>"""
    try:
        parsed = urllib.parse.urlparse(href)
        params = urllib.parse.parse_qs(parsed.query)
        u_param = params.get("u", [""])[0]
        if u_param.startswith("a1"):
            raw_b64 = u_param[2:]
            raw_b64 += "=" * ((4 - len(raw_b64) % 4) % 4)
            return base64.urlsafe_b64decode(raw_b64).decode("utf-8")
    except Exception:
        pass
    return href


class DuckDuckGoProvider(SearchProvider):
    """DuckDuckGo Free Search Provider with region fallback and direct Bing search resilience"""

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

            # Resilient direct search fallback if DDGS yields 0 results
            if not results:
                try:
                    url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
                    }
                    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                        r = client.get(url, headers=headers)
                        soup = BeautifulSoup(r.text, "html.parser")
                        for li in soup.select("li.b_algo"):
                            h2 = li.select_one("h2 a")
                            snippet = li.select_one(".b_caption p") or li.select_one(".b_algoSlug")
                            if h2:
                                raw_href = h2.get("href", "")
                                real_url = _decode_bing_url(raw_href)
                                title = h2.get_text().strip()
                                b = snippet.get_text().strip() if snippet else ""
                                if real_url and title:
                                    results.append(
                                        SearchResultItem(
                                            title=title,
                                            url=real_url,
                                            snippet=b
                                        )
                                    )
                                    if len(results) >= max_results:
                                        break
                except Exception as e:
                    logger.warning(f"Direct search fallback failed for '{query}': {e}")

            return results

        return await asyncio.to_thread(_sync_search)
