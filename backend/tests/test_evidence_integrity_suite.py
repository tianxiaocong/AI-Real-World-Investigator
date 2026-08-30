import pytest
from app.models.verification_models import (
    Source,
    SourceTier,
    Evidence,
    EvidenceDirectness,
    SourceProvenance,
    ProvenanceType,
    Verifiability,
    EvidenceState,
    Claim,
    InputType
)
from app.engine.verdict_rules import (
    assess_evidence_for_claim,
    compute_evidence_state,
    _resolve_ultimate_origin,
    resolve_provenance_target
)
from app.agents.verifier import VerificationAgent
from app.agents.claim_extractor import ClaimExtractorAgent
from app.scraper.extractor import WebScraper


def make_test_claim(cid: str, statement: str) -> Claim:
    return Claim(
        id=cid,
        original_input=statement,
        input_type=InputType.TEXT,
        statement=statement,
        claim_index=0,
        verifiability=Verifiability.PUBLICLY_VERIFIABLE,
        verifiability_reason="Test statement for verification invariant",
        verified_as_of="2026-08-30"
    )


class MockLLMForHallucination:
    """Mock LLM that hallucinates an exact_quote that does not exist in text."""
    async def generate_structured(self, prompt, response_model, system_prompt=None, temperature=0.0):
        from app.agents.claim_extractor import ClaimExtractionBatch, RawExtractedClaim
        from app.models.schemas import ClaimType, ConfidenceLevel
        return ClaimExtractionBatch(
            claims=[
                RawExtractedClaim(
                    statement="Company XYZ reported $50 billion profit in 2024.",
                    claim_type=ClaimType.FACT_STATEMENT,
                    confidence=ConfidenceLevel.HIGH,
                    reasoning="Extracted from text",
                    exact_quote="Company XYZ posted astronomical $50 billion pure profit exceeding all targets in 2024."
                )
            ]
        )


@pytest.mark.asyncio
async def test_hallucinated_quote_blocked_at_extractor():
    """
    Invariant 1: An LLM hallucinated quote that fails physical anchor location
    MUST be discarded immediately at the extractor stage and cannot leak into results.
    """
    raw_document = "The board of directors met on Tuesday to discuss executive compensation and operational matters."
    extractor = ClaimExtractorAgent(llm_provider=MockLLMForHallucination())
    
    extracted = await extractor.extract_claims_from_source(
        clean_text=raw_document,
        target_name="Company XYZ",
        source_url="https://example.com/press"
    )
    
    # Must be completely discarded, returning 0 unverified claims
    assert len(extracted) == 0, f"Expected 0 claims due to UNVERIFIED quote discard, but got {len(extracted)}"


@pytest.mark.asyncio
async def test_fuzzy_quote_cannot_become_direct_evidence_in_verifier():
    """
    Invariant 2: A FUZZY quote match must strictly be treated as non-supporting CONTEXTUAL,
    never granted DIRECT admissibility or direct support.
    """
    agent = VerificationAgent(llm_provider=None)
    claim_dict = {
        "id": "c-01",
        "statement": "The company grew by 25%.",
        "claim_type": "FACT_STATEMENT",
        "sources": [
            {
                "id": "s-01",
                "domain": "news.com",
                "title": "Quarterly Report",
                "url": "https://news.com/q3",
                "exact_quote": "The company leaped forward by 25%.",  # Slightly altered
                "quote_match": "FUZZY",
                "char_start": 10,
                "char_end": 44
            }
        ]
    }
    
    results = await agent.verify_and_cluster_claims([claim_dict])
    assert len(results) == 1
    res = results[0]
    
    # Direct support MUST be False and supporting evidence count MUST be 0!
    assert res["has_direct_support"] is False, "Security Invariant Violated: FUZZY quote granted direct support!"
    assert res["supporting_evidence_count"] == 0
    assert res["evidence_state"] == EvidenceState.INSUFFICIENT.value


def test_unrelated_sources_do_not_inflate_sufficient_verdict():
    """
    Invariant 3 (P0 Red Team Fix):
    1 Official Supporting Source + 2 Unrelated Non-Supporting Sources
    MUST NOT produce EvidenceState.SUFFICIENT.
    Previously, independent_source_count=3 and has_direct_support=True inflated this to SUFFICIENT.
    """
    claim = make_test_claim("c-01", "Company ABC launched Model X in 2025.")
    
    # 3 independent sources from 3 separate domains
    src_official = Source(id="s-off", title="Model X Launch Official Press", domain="companyabc.com", url="https://companyabc.com/launch", source_tier=SourceTier.OFFICIAL)
    src_unrelated_1 = Source(id="s-unrel-1", title="Gaming Forum", domain="reddit.com", url="https://reddit.com/r/gaming/1", source_tier=SourceTier.COMMUNITY)
    src_unrelated_2 = Source(id="s-unrel-2", title="Celebrity Gossip", domain="dailymail.co.uk", url="https://dailymail.co.uk/gossip/2", source_tier=SourceTier.MAINSTREAM)
    
    sources = [src_official, src_unrelated_1, src_unrelated_2]
    
    # Only 1 direct supporting evidence from the official source!
    ev_supporting = Evidence(
        id="e-1",
        source_id="s-off",
        claim_id="c-01",
        exact_quote="Company ABC officially launched Model X today.",
        directness=EvidenceDirectness.DIRECT,
        supports_claim=True,
        contradicts_claim=False,
        scope_match=True
    )
    # The other 2 sources provide only non-supporting background context
    ev_unrelated_1 = Evidence(
        id="e-2",
        source_id="s-unrel-1",
        claim_id="c-01",
        exact_quote="",
        directness=EvidenceDirectness.CONTEXTUAL,
        supports_claim=False,
        contradicts_claim=False,
        scope_match=False
    )
    ev_unrelated_2 = Evidence(
        id="e-3",
        source_id="s-unrel-2",
        claim_id="c-01",
        exact_quote="",
        directness=EvidenceDirectness.CONTEXTUAL,
        supports_claim=False,
        contradicts_claim=False,
        scope_match=False
    )
    
    evidences = [ev_supporting, ev_unrelated_1, ev_unrelated_2]
    
    assessment = assess_evidence_for_claim(claim, sources, evidences, [])
    
    # 3 total sources found, 3 independent sources in manifest
    assert assessment.total_sources_found == 3
    assert assessment.independent_source_count == 3
    
    # BUT direct supporting origins MUST BE EXACTLY 1!
    assert assessment.direct_supporting_origin_count == 1
    assert assessment.has_strong_independent_support is False
    
    # Compute verdict state
    verdict_state = compute_evidence_state(assessment, Verifiability.PUBLICLY_VERIFIABLE)
    
    # MUST NOT BE SUFFICIENT! (Requires >= 2 independent supporting origins)
    assert verdict_state != EvidenceState.SUFFICIENT, "Security Invariant Violated: Unrelated sources inflated verdict to SUFFICIENT!"
    assert verdict_state == EvidenceState.INSUFFICIENT


def test_republication_chain_does_not_inflate_sufficient_verdict():
    """
    Invariant 4:
    Source S1 (Official) publishes news.
    Source S2 (Reuters) republishes S1.
    Source S3 (TechBlog) republishes S2.
    All 3 provide direct quotes, but all trace back to root S1.
    direct_supporting_origin_count MUST be 1, preventing false SUFFICIENT verdict.
    """
    claim = make_test_claim("c-01", "CEO John Doe resigned on August 15.")
    
    s1 = Source(id="s1", title="Official Statement", domain="official.org", url="https://official.org/pr/1", source_tier=SourceTier.OFFICIAL)
    s2 = Source(id="s2", title="Reuters Wire", domain="reuters.com", url="https://reuters.com/wire/2", source_tier=SourceTier.AUTHORITATIVE)
    s3 = Source(id="s3", title="TechBlog Post", domain="techblog.net", url="https://techblog.net/post/3", source_tier=SourceTier.COMMUNITY)
    
    sources = [s1, s2, s3]
    
    # S3 republishes S2; S2 republishes S1
    prov_edges = [
        SourceProvenance(source_id="s3", origin_source_id="s2", provenance_type=ProvenanceType.REPUBLISHES),
        SourceProvenance(source_id="s2", origin_source_id="s1", provenance_type=ProvenanceType.REPUBLISHES)
    ]
    
    evidences = [
        Evidence(id="e1", source_id="s1", claim_id="c-01", exact_quote="John Doe has resigned.", directness=EvidenceDirectness.DIRECT, supports_claim=True, scope_match=True),
        Evidence(id="e2", source_id="s2", claim_id="c-01", exact_quote="According to official.org, John Doe has resigned.", directness=EvidenceDirectness.DIRECT, supports_claim=True, scope_match=True),
        Evidence(id="e3", source_id="s3", claim_id="c-01", exact_quote="TechBlog reports John Doe has resigned via Reuters.", directness=EvidenceDirectness.DIRECT, supports_claim=True, scope_match=True)
    ]
    
    assessment = assess_evidence_for_claim(claim, sources, evidences, prov_edges)
    
    # Although 3 sources and 3 evidences exist, ultimate origin resolution collapses them to 1
    assert assessment.origin_source_count == 1
    assert assessment.republish_count == 2
    assert assessment.direct_supporting_origin_count == 1
    assert assessment.has_strong_independent_support is False
    
    verdict_state = compute_evidence_state(assessment, Verifiability.PUBLICLY_VERIFIABLE)
    assert verdict_state != EvidenceState.SUFFICIENT


def test_two_true_independent_official_origins_grant_sufficient():
    """
    Invariant 5:
    Two genuinely independent origins (e.g. Official SEC filing + Official Court filing)
    directly supporting with scope match and consistency MUST correctly yield SUFFICIENT.
    """
    claim = make_test_claim("c-01", "Company ABC agreed to pay a $10M settlement.")
    
    s_sec = Source(id="s-sec", title="SEC Litigation Release", domain="sec.gov", url="https://sec.gov/litigation/1", source_tier=SourceTier.OFFICIAL)
    s_court = Source(id="s-court", title="Court Final Judgment", domain="court.gov", url="https://court.gov/docket/2", source_tier=SourceTier.OFFICIAL)
    
    sources = [s_sec, s_court]
    
    evidences = [
        Evidence(id="e1", source_id="s-sec", claim_id="c-01", exact_quote="Company ABC agreed to pay $10 million settlement.", directness=EvidenceDirectness.DIRECT, supports_claim=True, scope_match=True),
        Evidence(id="e2", source_id="s-court", claim_id="c-01", exact_quote="Final judgment approves $10 million settlement against Company ABC.", directness=EvidenceDirectness.DIRECT, supports_claim=True, scope_match=True)
    ]
    
    assessment = assess_evidence_for_claim(claim, sources, evidences, [])
    
    assert assessment.direct_supporting_origin_count == 2
    assert assessment.has_strong_independent_support is True
    assert assessment.has_supporting_official_source is True
    
    verdict_state = compute_evidence_state(assessment, Verifiability.PUBLICLY_VERIFIABLE)
    assert verdict_state == EvidenceState.SUFFICIENT
