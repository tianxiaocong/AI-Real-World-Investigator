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
    def locate_quote_spans(clean_text: str, quote: str) -> Tuple[Optional[int], Optional[int], Optional[str], Optional[str], str, str, str]:
        """
        Locates the character position of a quote in the source text,
        along with surrounding context window for UI evidence inspection and match tier.
        Returns (char_start, char_end, prefix, suffix, match_tier, element_role, block_id)
        - EXACT: True verbatim raw substring match directly on clean_text where clean_text[start:end] == quote.
        - FUZZY: Normalized whitespace or case-insensitive match on normalized text.
        - UNVERIFIED: No reliable anchor found.
        """
        if not clean_text or not quote:
            return None, None, None, None, "UNVERIFIED", "UNKNOWN", ""

        raw_quote = quote.strip()
        if not raw_quote:
            return None, None, None, None, "UNVERIFIED", "UNKNOWN", ""

        # --- NEW: DOM Provenance Extraction ---
        element_role = "MAIN"
        block_id = ""
        
        # Only parse if it looks like HTML
        if "<" in clean_text and ">" in clean_text:
            soup = BeautifulSoup(clean_text, "html.parser")
            found_element = None
            for text_node in soup.find_all(string=True):
                if raw_quote in text_node or raw_quote.lower() in text_node.lower():
                    found_element = text_node.parent
                    break
            
            if found_element:
                curr = found_element
                while curr and curr.name != '[document]':
                    if curr.name in ['aside', 'nav', 'footer', 'header']:
                        element_role = curr.name.upper()
                        b_id = curr.get('id')
                        b_class = curr.get('class')
                        if b_id:
                            block_id = f"{curr.name}#{b_id}"
                        elif b_class:
                            block_id = f"{curr.name}.{b_class[0]}"
                        else:
                            block_id = curr.name
                        break
                    curr = curr.parent

        # 1. True verbatim EXACT match directly on raw clean_text
        idx_raw = clean_text.find(raw_quote)
        if idx_raw != -1:
            char_start = idx_raw
            char_end = idx_raw + len(raw_quote)
            prefix = clean_text[max(0, char_start - 120):char_start]
            suffix = clean_text[char_end:min(len(clean_text), char_end + 120)]
            return char_start, char_end, prefix, suffix, "EXACT", element_role, block_id

        import re
        escaped_parts = [re.escape(w) for w in raw_quote.split()]

        # 2. Regex-based FUZZY match (handles case-insensitive and varying whitespace simultaneously)
        if escaped_parts:
            pattern = r'\s+'.join(escaped_parts)
            try:
                match = re.search(pattern, clean_text, flags=re.IGNORECASE)
                if match:
                    char_start = match.start()
                    char_end = match.end()
                    prefix = clean_text[max(0, char_start - 120):char_start]
                    suffix = clean_text[char_end:min(len(clean_text), char_end + 120)]
                    return char_start, char_end, prefix, suffix, "FUZZY", element_role, block_id
            except Exception as e:
                logger.warning(f"Regex error in quote matching: {e}")

        # 3. Fuzzy prefix anchor match
        if len(escaped_parts) > 4:
            prefix_parts = escaped_parts[:5]
            pattern = r'\s+'.join(prefix_parts)
            try:
                match = re.search(pattern, clean_text, flags=re.IGNORECASE)
                if match:
                    char_start = match.start()
                    char_end = min(len(clean_text), char_start + len(raw_quote))
                    prefix = clean_text[max(0, char_start - 100):char_start]
                    suffix = clean_text[char_end:min(len(clean_text), char_end + 100)]
                    return char_start, char_end, prefix, suffix, "FUZZY", element_role, block_id
            except Exception as e:
                pass

        return None, None, None, None, "UNVERIFIED", "UNKNOWN", ""
