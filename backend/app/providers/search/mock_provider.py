from typing import List
from app.providers.search.base import SearchProvider, SearchResultItem

class MockSearchProvider(SearchProvider):
    """Mock Search Provider for offline verification"""

    async def search(self, query: str, max_results: int = 5) -> List[SearchResultItem]:
        q_slug = query.replace(' ', '-').lower()
        return [
            SearchResultItem(
                title=f"[拟真演示信源] 权威财经快讯: {query}",
                url=f"mock://reuters.com/business/{q_slug}-analysis",
                snippet=f"关键事实报道关于 {query}。行业权威监测显示其近期业务快速推进，多方核心资方参与商业合作。",
                is_synthetic=True
            ),
            SearchResultItem(
                title=f"[拟真演示信源] 官方备案与合规公开通告: {query}",
                url=f"mock://sec.gov/edgar/data/{q_slug}",
                snippet=f"官方合规公开档案披露，证实 {query} 的注册资本、团队股权与运营架构处于合规状态。",
                is_synthetic=True
            ),
            SearchResultItem(
                title=f"[拟真演示信源] 社区评测与争议讨论: {query}",
                url=f"mock://reddit.com/r/tech/{q_slug}_discussion",
                snippet=f"行业从业者与部分早期用户讨论关于 {query} 的产品细节与部分交付预期差异。",
                is_synthetic=True
            )
        ]
