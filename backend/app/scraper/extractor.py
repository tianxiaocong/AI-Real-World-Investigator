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

import unicodedata

class WebScraper:
    """Robust Web Scraper with SSRF protection, Trafilatura extraction & exact span matching"""

    @staticmethod
    def extract_clean_text_deterministic(html_content: str) -> str:
        """
        Converts HTML to clean, standardized plain text with deterministic guarantees:
        - Unicode Normalization: NFC
        - Newline Normalization: \r\n and \r unified to \n
        - Strips unwanted script/style tags
        """
        if not html_content:
            return ""

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

        if not clean_text:
            clean_text = ""

        # 1. Newline normalization
        clean_text = clean_text.replace("\r\n", "\n").replace("\r", "\n")
        # 2. Unicode NFC normalization
        clean_text = unicodedata.normalize("NFC", clean_text)
        return clean_text.strip()

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

                clean_text = WebScraper.extract_clean_text_deterministic(html_content)

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
    def locate_quote_spans(
        clean_text: str,
        quote: str
    ) -> Tuple[Optional[int], Optional[int], Optional[str], Optional[str], str, str, str]:
        """
        Locates the exact character position of a quote in the source text,
        along with surrounding context window and strict invariant match tier.
        Returns:
            (char_start, char_end, prefix, suffix, match_tier, element_role, block_id)
        
        Strict Invariants:
        - match_tier == "EXACT":
            0 <= char_start < char_end <= len(clean_text)
            clean_text[char_start:char_end] == matched_quote (verbatim codepoint slice)
        - match_tier == "NORMALIZED_EXACT":
            0 <= char_start < char_end <= len(clean_text)
            clean_text[char_start:char_end] slices the raw text matching the quote
            under whitespace normalization.
        - match_tier == "FUZZY":
            Anchored via case-insensitive or sliding window regex.
        - match_tier == "UNVERIFIED":
            (None, None, None, None, "UNVERIFIED", "UNKNOWN", "")
        """
        if not clean_text or not quote:
            return None, None, None, None, "UNVERIFIED", "UNKNOWN", ""

        # Apply NFC Unicode normalization consistently
        norm_source = unicodedata.normalize("NFC", clean_text)
        norm_quote = unicodedata.normalize("NFC", quote)
        raw_quote = norm_quote.strip()

        if not raw_quote:
            return None, None, None, None, "UNVERIFIED", "UNKNOWN", ""

        # --- DOM Role / Element Hierarchy Extraction ---
        element_role = "MAIN"
        block_id = ""
        if "<" in norm_source and ">" in norm_source:
            try:
                soup = BeautifulSoup(norm_source, "html.parser")
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
            except Exception:
                pass

        # 1. Verbatim Substring Search (Full Quote with exact whitespace)
        idx_full = norm_source.find(norm_quote)
        if idx_full != -1 and len(norm_quote) > 0:
            char_start = idx_full
            char_end = idx_full + len(norm_quote)
            prefix = norm_source[max(0, char_start - 120):char_start]
            suffix = norm_source[char_end:min(len(norm_source), char_end + 120)]
            return char_start, char_end, prefix, suffix, "EXACT", element_role, block_id

        # 2. Verbatim Substring Search (Trimmed Quote)
        idx_raw = norm_source.find(raw_quote)
        if idx_raw != -1:
            char_start = idx_raw
            char_end = idx_raw + len(raw_quote)
            prefix = norm_source[max(0, char_start - 120):char_start]
            suffix = norm_source[char_end:min(len(norm_source), char_end + 120)]
            return char_start, char_end, prefix, suffix, "EXACT", element_role, block_id

        import re
        escaped_tokens = [re.escape(w) for w in raw_quote.split() if w]

        # 3. Normalized Exact Match (Arbitrary Whitespace / Newlines between exact tokens)
        if escaped_tokens:
            pattern_exact_case = r'\s+'.join(escaped_tokens)
            try:
                match = re.search(pattern_exact_case, norm_source)
                if match:
                    char_start = match.start()
                    char_end = match.end()
                    prefix = norm_source[max(0, char_start - 120):char_start]
                    suffix = norm_source[char_end:min(len(norm_source), char_end + 120)]
                    matched_slice = norm_source[char_start:char_end]
                    tier = "NORMALIZED_EXACT" if "".join(matched_slice.split()) == "".join(raw_quote.split()) else "FUZZY"
                    return char_start, char_end, prefix, suffix, tier, element_role, block_id
            except Exception as e:
                logger.debug(f"Regex error in exact case matching: {e}")

            # 4. Case-Insensitive Normalized Match
            try:
                match_ci = re.search(pattern_exact_case, norm_source, flags=re.IGNORECASE)
                if match_ci:
                    char_start = match_ci.start()
                    char_end = match_ci.end()
                    prefix = norm_source[max(0, char_start - 120):char_start]
                    suffix = norm_source[char_end:min(len(norm_source), char_end + 120)]
                    return char_start, char_end, prefix, suffix, "FUZZY", element_role, block_id
            except Exception as e:
                logger.debug(f"Regex error in case-insensitive matching: {e}")

        # 5. Sliding Anchor Matching for Lengthy Quotes (>= 5 tokens)
        if len(escaped_tokens) >= 5:
            prefix_pattern = r'\s+'.join(escaped_tokens[:4])
            try:
                match_p = re.search(prefix_pattern, norm_source, flags=re.IGNORECASE)
                if match_p:
                    char_start = match_p.start()
                    suffix_pattern = r'\s+'.join(escaped_tokens[-3:])
                    match_s = re.search(suffix_pattern, norm_source[char_start:], flags=re.IGNORECASE)
                    if match_s:
                        char_end = char_start + match_s.end()
                    else:
                        char_end = min(len(norm_source), char_start + len(raw_quote))
                    prefix = norm_source[max(0, char_start - 100):char_start]
                    suffix = norm_source[char_end:min(len(norm_source), char_end + 100)]
                    return char_start, char_end, prefix, suffix, "FUZZY", element_role, block_id
            except Exception as e:
                pass

        return None, None, None, None, "UNVERIFIED", "UNKNOWN", ""
