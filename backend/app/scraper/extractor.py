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
        source_text: str,
        quote: str
    ) -> Tuple[Optional[int], Optional[int], Optional[str], Optional[str], str, str, str]:
        """
        Locates the character position of a quote in the source text,
        along with surrounding context window and strictly verified match tiers.
        Returns:
            (char_start, char_end, prefix, suffix, match_tier, element_role, block_id)
        
        Strict Tier Definitions:
        - EXACT:
            Strict literal character-for-character equality:
            source_text[char_start:char_end] == quote (verbatim codepoint slice, zero modification).
        - NORMALIZED_EXACT:
            The exact token sequence matches in identical order and case, but with
            whitespace normalization (leading/trailing trim, multiple spaces, newlines, tabs).
            source_text[char_start:char_end] slices the raw text containing those exact tokens.
        - FUZZY:
            Case-insensitive match or prefix/suffix sliding anchor match.
        - UNVERIFIED:
            No reliable anchor found; returns None coordinates.
        """
        if not source_text or not quote:
            return None, None, None, None, "UNVERIFIED", "UNKNOWN", ""

        # --- Tier 1: True Verbatim EXACT Match (zero modification) ---
        idx_verbatim = source_text.find(quote)
        if idx_verbatim != -1 and len(quote) > 0:
            char_start = idx_verbatim
            char_end = idx_verbatim + len(quote)
            prefix = source_text[max(0, char_start - 120):char_start]
            suffix = source_text[char_end:min(len(source_text), char_end + 120)]
            element_role, block_id = WebScraper._extract_dom_role(source_text, quote)
            return char_start, char_end, prefix, suffix, "EXACT", element_role, block_id

        # --- Tier 2: NORMALIZED_EXACT (Whitespace / Trimming / Unicode variations) ---
        norm_source = unicodedata.normalize("NFC", source_text)
        norm_quote = unicodedata.normalize("NFC", quote)
        
        # If quote had leading/trailing whitespace, try finding trimmed quote
        trimmed_quote = norm_quote.strip()
        if not trimmed_quote:
            return None, None, None, None, "UNVERIFIED", "UNKNOWN", ""

        import re
        tokens = trimmed_quote.split()
        if tokens:
            escaped_tokens = [re.escape(w) for w in tokens]
            pattern_exact_tokens = r'\s+'.join(escaped_tokens)
            try:
                match_norm = re.search(pattern_exact_tokens, norm_source)
                if match_norm:
                    char_start = match_norm.start()
                    char_end = match_norm.end()
                    prefix = norm_source[max(0, char_start - 120):char_start]
                    suffix = norm_source[char_end:min(len(norm_source), char_end + 120)]
                    element_role, block_id = WebScraper._extract_dom_role(norm_source, trimmed_quote)
                    return char_start, char_end, prefix, suffix, "NORMALIZED_EXACT", element_role, block_id
            except Exception as e:
                logger.debug(f"Regex error in exact tokens matching: {e}")

            # --- Tier 3: FUZZY (Case-insensitive or sliding window) ---
            try:
                match_ci = re.search(pattern_exact_tokens, norm_source, flags=re.IGNORECASE)
                if match_ci:
                    char_start = match_ci.start()
                    char_end = match_ci.end()
                    prefix = norm_source[max(0, char_start - 120):char_start]
                    suffix = norm_source[char_end:min(len(norm_source), char_end + 120)]
                    element_role, block_id = WebScraper._extract_dom_role(norm_source, trimmed_quote)
                    return char_start, char_end, prefix, suffix, "FUZZY", element_role, block_id
            except Exception as e:
                logger.debug(f"Regex error in case-insensitive matching: {e}")

            # Sliding Anchor Matching for Lengthy Quotes (>= 5 tokens)
            if len(tokens) >= 5:
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
                            char_end = min(len(norm_source), char_start + len(trimmed_quote))
                        prefix = norm_source[max(0, char_start - 100):char_start]
                        suffix = norm_source[char_end:min(len(norm_source), char_end + 100)]
                        element_role, block_id = WebScraper._extract_dom_role(norm_source, trimmed_quote)
                        return char_start, char_end, prefix, suffix, "FUZZY", element_role, block_id
                except Exception as e:
                    pass

        # --- Tier 4: UNVERIFIED ---
        return None, None, None, None, "UNVERIFIED", "UNKNOWN", ""

    @staticmethod
    def _extract_dom_role(source_text: str, quote: str) -> Tuple[str, str]:
        """Helper to extract DOM element role and block ID if source text is HTML."""
        element_role = "MAIN"
        block_id = ""
        if "<" in source_text and ">" in source_text:
            try:
                soup = BeautifulSoup(source_text, "html.parser")
                found_element = None
                raw_q = quote.strip()
                for text_node in soup.find_all(string=True):
                    if raw_q in text_node or raw_q.lower() in text_node.lower():
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
        return element_role, block_id
