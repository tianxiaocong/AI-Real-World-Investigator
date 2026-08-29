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


def test_unicode_nfc_nfd_normalization_in_normalized_exact():
    import unicodedata
    # Base composed text (NFC) vs Decomposed input quote (NFD)
    # e.g., 'é' composed (\u00e9) vs 'e' + combining acute accent (\u0065\u0301)
    nfc_source = "Le café de Paris a annoncé ses résultats financiers."
    nfd_quote = unicodedata.normalize("NFD", "café de Paris")
    
    # In NFD, len("café") is 5 bytes/chars, while in NFC it is 4
    start, end, prefix, suffix, tier, role, block_id = WebScraper.locate_quote_spans(nfc_source, nfd_quote)
    
    # NFD quote cannot verbatim match NFC source without normalization -> strictly NORMALIZED_EXACT
    assert tier == "NORMALIZED_EXACT"
    assert start is not None and end is not None
    assert "café de Paris" in nfc_source[start:end]


def test_sliding_anchor_matching_ocr_drift():
    source_text = "The quick brown fox jumps over the lazy dog and runs into the deep green forest near the flowing river."
    # Quote with internal OCR / layout word drift ("leaps" instead of "jumps", "dense" instead of "deep green")
    tampered_ocr_quote = "The quick brown fox leaps over the lazy dog and runs into the dense forest"
    
    start, end, prefix, suffix, tier, role, block_id = WebScraper.locate_quote_spans(source_text, tampered_ocr_quote)
    
    # Lengthy quote with prefix/suffix anchors but internal OCR drift -> strictly FUZZY
    assert tier == "FUZZY"
    assert start is not None and end is not None
    assert start == 0
    assert "The quick brown fox" in source_text[start:end]


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


@pytest.mark.asyncio
async def test_e2e_claim_extractor_quote_immutability_and_normalization():
    """
    Validates end-to-end production invariant in ClaimExtractorAgent:
    - Input raw source contains 'AAA hello world BBB'
    - LLM returns exact_quote with leading/trailing spaces: '  hello world  '
    - Invariant 1: exact_quote in returned dict is strictly unmutated ('  hello world  ')
    - Invariant 2: match_tier is strictly NORMALIZED_EXACT (NOT EXACT!)
    - Invariant 3: char_start and char_end slice the raw source: source[start:end] == 'hello world'
    """
    from app.agents.claim_extractor import ClaimExtractorAgent, ClaimExtractionBatch, RawExtractedClaim
    from unittest.mock import AsyncMock
    
    mock_llm = AsyncMock()
    mock_llm.generate_structured.return_value = ClaimExtractionBatch(
        claims=[
            RawExtractedClaim(
                statement="A test statement.",
                claim_type="FACT_STATEMENT",
                confidence="HIGH",
                exact_quote="  hello world  ",  # LLM returned padded quote
                reasoning="Test reasoning"
            )
        ]
    )
    
    extractor = ClaimExtractorAgent(llm_provider=mock_llm)
    source_text = "AAA hello world BBB"
    
    results = await extractor.extract_claims_from_source(
        source_text=source_text,
        source_url="https://example.com/test",
        source_type="OFFICIAL",
        target_name="test target"
    )
    
    assert len(results) == 1
    res = results[0]
    
    # Invariant 1: raw exact_quote preserved strictly unmodified
    assert res["exact_quote"] == "  hello world  "
    # Invariant 2: Tier is strictly NORMALIZED_EXACT (not EXACT because of padding)
    assert res["quote_match"] == "NORMALIZED_EXACT"
    # Invariant 3: Offsets slice the matching tokens in source text
    start, end = res["char_start"], res["char_end"]
    assert source_text[start:end] == "hello world"


@pytest.mark.asyncio
async def test_e2e_claim_extractor_verbatim_exact():
    """
    Validates verbatim EXACT path in ClaimExtractorAgent when LLM outputs exact substring.
    """
    from app.agents.claim_extractor import ClaimExtractorAgent, ClaimExtractionBatch, RawExtractedClaim
    from unittest.mock import AsyncMock
    
    mock_llm = AsyncMock()
    mock_llm.generate_structured.return_value = ClaimExtractionBatch(
        claims=[
            RawExtractedClaim(
                statement="Verbatim statement.",
                claim_type="FACT_STATEMENT",
                confidence="HIGH",
                exact_quote="hello world",  # exact verbatim substring
                reasoning="Verbatim reasoning"
            )
        ]
    )
    
    extractor = ClaimExtractorAgent(llm_provider=mock_llm)
    source_text = "AAA hello world BBB"
    
    results = await extractor.extract_claims_from_source(
        source_text=source_text,
        source_url="https://example.com/test",
        source_type="OFFICIAL",
        target_name="test target"
    )
    
    assert len(results) == 1
    res = results[0]
    assert res["exact_quote"] == "hello world"
    assert res["quote_match"] == "EXACT"
    start, end = res["char_start"], res["char_end"]
    assert source_text[start:end] == "hello world"
