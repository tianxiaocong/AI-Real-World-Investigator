import hashlib
import logging
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlparse
import httpx
import trafilatura
from bs4 import BeautifulSoup
from app.core.security import is_safe_url, classify_source_and_credibility
from app.models.schemas import SourceCreate

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
}

class WebScraper:
    """Robust Web Scraper with SSRF protection, Trafilatura extraction & exact span matching"""

    @staticmethod
    async def fetch_and_extract(url: str, timeout_seconds: int = 15) -> Optional[SourceCreate]:
        """Fetch URL content, clean HTML, extract main text and compute metadata"""
        if not is_safe_url(url):
            logger.warning(f"SSRF check rejected URL: {url}")
            return None

        parsed = urlparse(url)
        domain = parsed.hostname or ""
        source_type, credibility = classify_source_and_credibility(url, domain)

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True, headers=HEADERS) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    logger.warning(f"HTTP {response.status_code} for {url}")
                    return None

                html_content = response.text
                if not html_content:
                    return None

                # Primary extraction with trafilatura
                clean_text = trafilatura.extract(
                    html_content,
                    include_comments=False,
                    include_tables=True,
                    no_fallback=False
                )

                # Fallback to BeautifulSoup if trafilatura yields minimal text
                if not clean_text or len(clean_text.strip()) < 100:
                    soup = BeautifulSoup(html_content, "html.parser")
                    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                        tag.decompose()
                    clean_text = soup.get_text(separator="\n", strip=True)

                if not clean_text or len(clean_text.strip()) < 80:
                    logger.warning(f"Insufficient content extracted from {url}")
                    return None

                # Extract page title
                soup = BeautifulSoup(html_content, "html.parser")
                title_tag = soup.find("title")
                title = title_tag.get_text(strip=True) if title_tag else None

                # Compute content hash for deduplication
                content_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()

                return SourceCreate(
                    url=url,
                    domain=domain,
                    title=title,
                    source_type=source_type,
                    credibility_score=credibility,
                    clean_text=clean_text,
                    raw_content=html_content[:50000],  # keep max 50KB raw snippet
                    content_hash=content_hash,
                    source_metadata={"char_count": len(clean_text)}
                )

        except Exception as e:
            logger.warning(f"Failed to scrape {url}: {e}")
            return None

    @staticmethod
    def locate_quote_spans(clean_text: str, quote: str) -> Tuple[Optional[int], Optional[int], Optional[str], Optional[str], str]:
        """
        Locates the character position of a quote in the source text,
        along with surrounding context window for UI evidence inspection and match tier.
        Returns (char_start, char_end, prefix, suffix, match_tier: EXACT|FUZZY|UNVERIFIED)
        - EXACT: True verbatim raw substring match directly on clean_text where clean_text[start:end] == quote.
        - FUZZY: Normalized whitespace or case-insensitive match on normalized text.
        - UNVERIFIED: No reliable anchor found.
        """
        if not clean_text or not quote:
            return None, None, None, None, "UNVERIFIED"

        raw_quote = quote.strip()

        # 1. True verbatim EXACT match directly on raw clean_text
        idx_raw = clean_text.find(raw_quote)
        if idx_raw != -1:
            char_start = idx_raw
            char_end = idx_raw + len(raw_quote)
            prefix = clean_text[max(0, char_start - 120):char_start]
            suffix = clean_text[char_end:min(len(clean_text), char_end + 120)]
            return char_start, char_end, prefix, suffix, "EXACT"

        # 2. Case-insensitive match on raw clean_text
        idx_raw_lower = clean_text.lower().find(raw_quote.lower())
        if idx_raw_lower != -1:
            char_start = idx_raw_lower
            char_end = idx_raw_lower + len(raw_quote)
            prefix = clean_text[max(0, char_start - 120):char_start]
            suffix = clean_text[char_end:min(len(clean_text), char_end + 120)]
            return char_start, char_end, prefix, suffix, "FUZZY"

        # 3. Normalized whitespace match
        clean_text_norm = " ".join(clean_text.split())
        quote_norm = " ".join(raw_quote.split())

        idx_norm = clean_text_norm.find(quote_norm)
        if idx_norm != -1:
            char_start = idx_norm
            char_end = idx_norm + len(quote_norm)
            prefix = clean_text_norm[max(0, char_start - 120):char_start]
            suffix = clean_text_norm[char_end:min(len(clean_text_norm), char_end + 120)]
            return char_start, char_end, prefix, suffix, "FUZZY"

        # 4. Fuzzy prefix anchor match
        if len(quote_norm) > 30:
            prefix_sub = quote_norm[:30]
            idx_sub = clean_text_norm.find(prefix_sub)
            if idx_sub != -1:
                char_start = idx_sub
                char_end = idx_sub + len(quote_norm)
                prefix = clean_text_norm[max(0, char_start - 100):char_start]
                suffix = clean_text_norm[min(len(clean_text_norm), char_end):min(len(clean_text_norm), char_end + 100)]
                return char_start, char_end, prefix, suffix, "FUZZY"

        return None, None, None, None, "UNVERIFIED"
