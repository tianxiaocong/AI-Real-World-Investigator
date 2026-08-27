from typing import List
from app.providers.search.base import SearchProvider, SearchResultItem

class MockSearchProvider(SearchProvider):
    """Mock Search Provider for offline verification"""

    async def search(self, query: str, max_results: int = 5) -> List[SearchResultItem]:
        return [
            SearchResultItem(
                title=f"Official Investigation Brief on {query}",
                url=f"https://www.reuters.com/business/{query.replace(' ', '-').lower()}-analysis",
                snippet=f"Key factual reporting regarding {query}. Industry reports indicate sustained growth and active commercial partnerships in recent quarters."
            ),
            SearchResultItem(
                title=f"Regulatory Filings & Overview: {query}",
                url=f"https://www.sec.gov/edgar/data/{query.replace(' ', '_').lower()}",
                snippet=f"Official government disclosures and verified financial metrics related to {query} operations and funding structures."
            ),
            SearchResultItem(
                title=f"Community Discussion & Controversy: {query}",
                url=f"https://www.reddit.com/r/technology/comments/{query.replace(' ', '_').lower()}_discussion",
                snippet=f"Users and employees discuss alleged internal delays and product roadmap disagreements concerning {query}."
            )
        ]
