"""
AI Claim Verifier — Quote Anchoring & Precision Regression Tests
Validates:
1. EXACT match guarantees: clean_text[start:end] == quote
2. Whitespace / Case normalization falls back to FUZZY
3. Phantom quotes return UNVERIFIED
"""

import pytest
from app.scraper.extractor import WebScraper


def test_quote_anchoring_verbatim_exact():
    raw_text = "杭州宇树科技有限公司于2024年宣布完成近10亿元人民币B2轮融资，美团参与领投。"
    target_quote = "完成近10亿元人民币B2轮融资"

    start, end, prefix, suffix, tier, element_role, block_id = WebScraper.locate_quote_spans(raw_text, target_quote)

    assert tier == "EXACT"
    assert start is not None
    assert end is not None
    assert raw_text[start:end] == target_quote


def test_quote_anchoring_multiline_whitespace_fallback_fuzzy():
    raw_text = "OpenAI reported    substantial revenue growth\n\nin the fiscal year 2025."
    # Quote with single space between reported and substantial
    target_quote = "reported substantial revenue growth"

    start, end, prefix, suffix, tier, element_role, block_id = WebScraper.locate_quote_spans(raw_text, target_quote)

    # Since raw text has 4 spaces and not a single space, verbatim raw find fails,
    # and normalized whitespace find succeeds -> correctly matched as NORMALIZED_EXACT
    assert tier in ("NORMALIZED_EXACT", "FUZZY")


def test_quote_anchoring_case_insensitive_fallback_fuzzy():
    raw_text = "Elon musk acquired Twitter in 2022."
    target_quote = "Elon Musk acquired Twitter"

    start, end, prefix, suffix, tier, element_role, block_id = WebScraper.locate_quote_spans(raw_text, target_quote)

    # Different casing (Musk vs musk) -> downgraded to FUZZY
    assert tier == "FUZZY"


def test_quote_anchoring_phantom_quote_unverified():
    raw_text = "公司发布了全新的四足机器人产品。"
    phantom_quote = "公司宣布全面进军火星房地产开发领域"

    start, end, prefix, suffix, tier, element_role, block_id = WebScraper.locate_quote_spans(raw_text, phantom_quote)

    assert tier == "UNVERIFIED"
    assert start is None
    assert end is None


def test_quote_anchoring_offset_correctness():
    # Double space in raw text, single space in target quote
    raw_text = "This is an AI  Investigator example."
    target_quote = "AI Investigator"

    start, end, prefix, suffix, tier, element_role, block_id = WebScraper.locate_quote_spans(raw_text, target_quote)

    assert tier in ("NORMALIZED_EXACT", "FUZZY")
    # Offsets should map exactly to the raw text, meaning they capture the double space
    assert start == 11
    assert end == 27
    assert raw_text[start:end] == "AI  Investigator"


def test_quote_anchoring_repeated_quote():
    raw_text = "The AI Investigator tool is great. I love the AI Investigator tool."
    target_quote = "AI Investigator"

    start, end, prefix, suffix, tier, element_role, block_id = WebScraper.locate_quote_spans(raw_text, target_quote)

    # Should match the FIRST occurrence perfectly
    assert tier == "EXACT"
    assert start == 4
    assert end == 19
    assert raw_text[start:end] == target_quote
