import pytest
from app.scraper.extractor import WebScraper


def test_verbatim_exact_invariant_ascii():
    source_text = "OpenAI announced ChatGPT Plus at a subscription price of $20 per month on February 1, 2023."
    quote = "$20 per month on February 1, 2023."
    
    start, end, prefix, suffix, tier, role, block_id = WebScraper.locate_quote_spans(source_text, quote)
    
    assert tier == "EXACT"
    assert start is not None and end is not None
    # Strict Mathematical Invariant: source_text[start:end] MUST equal quote literally
    assert source_text[start:end] == quote
    assert prefix == "OpenAI announced ChatGPT Plus at a subscription price of "
    assert suffix == ""


def test_verbatim_exact_invariant_chinese():
    source_text = "宇树科技于2024年完成近10亿元人民币B2轮融资，由美团战略领投，金石投资跟投。"
    quote = "完成近10亿元人民币B2轮融资，由美团战略领投"
    
    start, end, prefix, suffix, tier, role, block_id = WebScraper.locate_quote_spans(source_text, quote)
    
    assert tier == "EXACT"
    assert start is not None and end is not None
    # Strict Mathematical Invariant
    assert source_text[start:end] == quote
    assert prefix == "宇树科技于2024年"
    assert suffix == "，金石投资跟投。"


def test_whitespace_padded_quote_returns_normalized_exact():
    source_text = "The Federal Trade Commission filed an administrative complaint to block Microsoft from acquiring Activision Blizzard."
    padded_quote = "  an administrative complaint to block Microsoft   "
    
    start, end, prefix, suffix, tier, role, block_id = WebScraper.locate_quote_spans(source_text, padded_quote)
    
    # Must NOT pretend to be EXACT because quote had padding; MUST be NORMALIZED_EXACT
    assert tier == "NORMALIZED_EXACT"
    assert start is not None and end is not None
    # Slice matches the raw text token sequence
    assert source_text[start:end] == "an administrative complaint to block Microsoft"


def test_normalized_exact_newline_variations():
    source_text = "DeepSeek-V3 achieved\nstate-of-the-art results across mathematical benchmarks\nand coding evaluations."
    quote = "DeepSeek-V3 achieved state-of-the-art results across mathematical benchmarks and coding evaluations."
    
    start, end, prefix, suffix, tier, role, block_id = WebScraper.locate_quote_spans(source_text, quote)
    
    # Tokens match with identical order and case across newlines -> NORMALIZED_EXACT
    assert tier == "NORMALIZED_EXACT"
    assert start is not None and end is not None
    assert "DeepSeek-V3 achieved" in source_text[start:end]
    assert "coding evaluations." in source_text[start:end]


def test_normalized_exact_multiple_spaces():
    source_text = "NVIDIA reported   record-breaking   quarterly revenue."
    quote = "NVIDIA reported record-breaking quarterly revenue."
    
    start, end, prefix, suffix, tier, role, block_id = WebScraper.locate_quote_spans(source_text, quote)
    
    assert tier == "NORMALIZED_EXACT"
    assert start is not None and end is not None
    assert source_text[start:end] == "NVIDIA reported   record-breaking   quarterly revenue."


def test_smart_quotes_and_unicode_symbols():
    source_text = "According to the FDA: “The Agency has determined that the drug is safe and effective.”"
    quote = "“The Agency has determined that the drug is safe and effective.”"
    
    start, end, prefix, suffix, tier, role, block_id = WebScraper.locate_quote_spans(source_text, quote)
    
    assert tier == "EXACT"
    assert start is not None and end is not None
    assert source_text[start:end] == quote


def test_case_insensitive_fuzzy_matching():
    source_text = "NVIDIA reported revenue for the second quarter of fiscal 2025 of $30.0 billion."
    quote = "nvidia reported revenue for the second quarter of fiscal 2025 of $30.0 billion."
    
    start, end, prefix, suffix, tier, role, block_id = WebScraper.locate_quote_spans(source_text, quote)
    
    # Case difference -> strictly FUZZY
    assert tier == "FUZZY"
    assert start is not None and end is not None
    assert source_text[start:end].lower() == quote.lower()


def test_sliding_anchor_matching():
    source_text = "The quick brown fox jumps over the lazy dog and runs into the forest near the river."
    # Quote with slight middle word modification
    tampered_quote = "The quick brown fox leaps over the lazy dog and runs into the forest"
    
    start, end, prefix, suffix, tier, role, block_id = WebScraper.locate_quote_spans(source_text, tampered_quote)
    
    assert tier == "FUZZY"
    assert start is not None and end is not None
    assert start == 0


def test_hallucinated_quote_returns_unverified():
    source_text = "Apple reported strong sales for the Mac lineup in Q4."
    hallucinated_quote = "Tesla acquired Microsoft for $1 trillion in cash."
    
    start, end, prefix, suffix, tier, role, block_id = WebScraper.locate_quote_spans(source_text, hallucinated_quote)
    
    assert tier == "UNVERIFIED"
    assert start is None
    assert end is None
    assert prefix is None
    assert suffix is None


def test_empty_or_whitespace_quote():
    source_text = "Valid source text."
    
    s1, e1, p1, suf1, t1, r1, b1 = WebScraper.locate_quote_spans(source_text, "")
    assert t1 == "UNVERIFIED"
    assert s1 is None
    
    s2, e2, p2, suf2, t2, r2, b2 = WebScraper.locate_quote_spans(source_text, "   \n\t  ")
    assert t2 == "UNVERIFIED"
    assert s2 is None
    
    s3, e3, p3, suf3, t3, r3, b3 = WebScraper.locate_quote_spans("", "Valid quote")
    assert t3 == "UNVERIFIED"
    assert s3 is None


def test_dom_element_role_detection():
    html_text = """
    <html>
        <body>
            <header>Header content</header>
            <main>
                <article>Main article content confirming revenue of 100M.</article>
            </main>
            <aside id="trending-news" class="sidebar-block">
                <p>Nvidia Blackwell chip production reportedly delayed indefinitely.</p>
            </aside>
            <footer>Footer content</footer>
        </body>
    </html>
    """
    quote = "Nvidia Blackwell chip production reportedly delayed indefinitely."
    
    start, end, prefix, suffix, tier, role, block_id = WebScraper.locate_quote_spans(html_text, quote)
    
    assert tier == "EXACT"
    assert role == "ASIDE"
    assert block_id == "aside#trending-news"
