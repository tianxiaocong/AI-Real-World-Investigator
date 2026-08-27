from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel

class SearchResultItem(BaseModel):
    title: str
    url: str
    snippet: str
    published_date: Optional[str] = None
    score: Optional[float] = None
    is_synthetic: bool = False

class SearchProvider(ABC):
    """Abstract Base Class for web search providers"""

    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> List[SearchResultItem]:
        """Execute web search and return standard list of SearchResultItems"""
        pass
