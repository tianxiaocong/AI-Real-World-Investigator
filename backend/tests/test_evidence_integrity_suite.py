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


# =========================================================================
# Phase 12: 8 Adversarial Evidence Integrity Invariant Tests (Tests 6 - 13)
# =========================================================================

def test_adversarial_6_domain_spoofing_resistance():
    """
    Invariant 6 (Adversarial Security):
    Attackers craft deceptive domain names resembling official regulatory portals
    (e.g. 'sec.gov.fake-filing.com' or 'www.fda.gov.attacker.net').
    The security classifier and source tiering MUST NOT categorize them as OFFICIAL/GOVERNMENT,
    and single attacker source quotes must never inflate verdict to SUFFICIENT.
    """
    from app.core.security import classify_source_and_credibility, SourceType
    
    spoofed_urls = [
        ("https://sec.gov.attacker.org/press/1", "sec.gov.attacker.org"),
        ("https://fda.gov.fake-pharma.cn/drug/2", "fda.gov.fake-pharma.cn"),
        ("https://who.int.malicious.xyz/alert/3", "who.int.malicious.xyz")
    ]
    for url, domain in spoofed_urls:
        st, cred = classify_source_and_credibility(url, domain)
        assert st != SourceType.GOVERNMENT, f"Spoofed domain {domain} improperly granted GOVERNMENT status!"
        assert cred < 0.90, f"Spoofed domain {domain} given unearned high credibility {cred}!"

    # Now verify verdict engine isolation:
    claim = make_test_claim("c-adv-06", "Regulator approved drug X.")
    s_fake = Source(id="s-fake", title="Fake SEC", domain="sec.gov.attacker.org", url="https://sec.gov.attacker.org/1", source_tier=SourceTier.COMMUNITY)
    ev_fake = Evidence(id="e-fake", source_id="s-fake", claim_id="c-adv-06", exact_quote="Regulator approved drug X.", directness=EvidenceDirectness.DIRECT, supports_claim=True, scope_match=True)
    
    assessment = assess_evidence_for_claim(claim, [s_fake], [ev_fake], [])
    assert assessment.has_supporting_official_source is False
    assert compute_evidence_state(assessment, Verifiability.PUBLICLY_VERIFIABLE) == EvidenceState.INSUFFICIENT


def test_adversarial_7_quantifier_scale_inflation_downgrades_to_insufficient():
    """
    Invariant 7 (Numeric Inflation):
    Claim asserts a massive number ('$4.7 billion settlement'), but source only proves
    a small fraction ('$4.7 million settlement').
    A HIGH severity QUANTIFIER ScopeIssue MUST be detected, blocking SUFFICIENT state.
    """
    from app.models.verification_models import ScopeIssue, ScopeIssueType, ScopeSeverity
    
    claim = make_test_claim("c-adv-07", "Company paid a $4.7 billion regulatory settlement.")
    s1 = Source(id="s1", title="Official Filing", domain="sec.gov", url="https://sec.gov/1", source_tier=SourceTier.OFFICIAL)
    s2 = Source(id="s2", title="Reuters Report", domain="reuters.com", url="https://reuters.com/1", source_tier=SourceTier.AUTHORITATIVE)
    
    # Evidence provides $4.7M, creating a High Quantifier mismatch
    quantifier_issue = ScopeIssue(
        issue_type=ScopeIssueType.QUANTIFIER,
        severity=ScopeSeverity.HIGH,
        source_fragment="$4.7 million",
        claim_fragment="$4.7 billion",
        explanation="Scale difference of 1000x between million and billion"
    )
    ev1 = Evidence(
        id="e1", source_id="s1", claim_id="c-adv-07",
        exact_quote="Company agreed to pay $4.7 million fine.",
        directness=EvidenceDirectness.DIRECT,
        supports_claim=True,
        scope_match=False,
        scope_issues=[quantifier_issue]
    )
    ev2 = Evidence(
        id="e2", source_id="s2", claim_id="c-adv-07",
        exact_quote="A $4.7 million penalty was confirmed.",
        directness=EvidenceDirectness.DIRECT,
        supports_claim=True,
        scope_match=False,
        scope_issues=[quantifier_issue]
    )
    
    assessment = assess_evidence_for_claim(claim, [s1, s2], [ev1, ev2], [])
    assert assessment.value_consistent is False
    verdict = compute_evidence_state(assessment, Verifiability.PUBLICLY_VERIFIABLE)
    assert verdict != EvidenceState.SUFFICIENT
    assert verdict == EvidenceState.INSUFFICIENT


def test_adversarial_8_temporal_mismatch_blocks_sufficient():
    """
    Invariant 8 (Temporal Mismatch):
    Claim claims an event took place in '2024', but evidence specifically anchors it to '2020'.
    HIGH severity TEMPORAL ScopeIssue must drop time_consistent to False,
    prohibiting a SUFFICIENT verdict.
    """
    from app.models.verification_models import ScopeIssue, ScopeIssueType, ScopeSeverity
    
    claim = make_test_claim("c-adv-08", "Company acquired Studio Z in 2024.")
    s1 = Source(id="s1", title="Official PR", domain="studioz.com", url="https://studioz.com/pr", source_tier=SourceTier.OFFICIAL)
    s2 = Source(id="s2", title="Bloomberg", domain="bloomberg.com", url="https://bloomberg.com/pr", source_tier=SourceTier.AUTHORITATIVE)
    
    time_issue = ScopeIssue(
        issue_type=ScopeIssueType.TEMPORAL,
        severity=ScopeSeverity.HIGH,
        source_fragment="in July 2020",
        claim_fragment="in 2024",
        explanation="Event occurred 4 years earlier than claimed"
    )
    ev1 = Evidence(
        id="e1", source_id="s1", claim_id="c-adv-08",
        exact_quote="Company finalized the acquisition of Studio Z in July 2020.",
        directness=EvidenceDirectness.DIRECT,
        supports_claim=True,
        scope_match=False,
        scope_issues=[time_issue]
    )
    ev2 = Evidence(
        id="e2", source_id="s2", claim_id="c-adv-08",
        exact_quote="The Studio Z buyout concluded back in 2020.",
        directness=EvidenceDirectness.DIRECT,
        supports_claim=True,
        scope_match=False,
        scope_issues=[time_issue]
    )
    
    assessment = assess_evidence_for_claim(claim, [s1, s2], [ev1, ev2], [])
    assert assessment.time_consistent is False
    verdict = compute_evidence_state(assessment, Verifiability.PUBLICLY_VERIFIABLE)
    assert verdict == EvidenceState.INSUFFICIENT


def test_adversarial_9_negative_assertion_unverifiable_yields_not_assessable():
    """
    Invariant 9 (Private/Non-Existent Negative Event):
    Claim asserts a purely private, unrecorded dinner conversation or non-existent event.
    Verifiability is NOT_PUBLICLY_VERIFIABLE.
    When 0 supporting sources exist, state MUST resolve to NOT_ASSESSABLE, never hallucinating support.
    """
    claim = Claim(
        id="c-adv-09",
        original_input="Executive told a friend at a private dinner that he will resign.",
        input_type=InputType.TEXT,
        statement="Executive told a friend at a private dinner that he will resign.",
        claim_index=0,
        verifiability=Verifiability.NOT_PUBLICLY_VERIFIABLE,
        verifiability_reason="Private verbal conversation with no public record",
        verified_as_of="2026-08-30"
    )
    assessment = assess_evidence_for_claim(claim, [], [], [])
    verdict = compute_evidence_state(assessment, claim.verifiability)
    assert verdict == EvidenceState.NOT_ASSESSABLE


def test_adversarial_10_community_source_cannot_override_official_refutation():
    """
    Invariant 10 (Refutation Integrity):
    An official authority issues a direct denial (e.g. Police statement refutes murder rumor).
    Multiple community forums (Reddit, Weibo gossip) post affirmative rumors claiming the murder is true.
    The presence of credible official contradiction MUST dominate and yield UNSUPPORTED or CONFLICTING,
    strictly preventing the rumor from receiving SUFFICIENT.
    """
    claim = make_test_claim("c-adv-10", "Celebrity died in a car crash yesterday.")
    
    s_police = Source(id="s-police", title="Police Official Bureau Statement", domain="police.gov", url="https://police.gov/pr/1", source_tier=SourceTier.OFFICIAL)
    s_rumor1 = Source(id="s-rumor1", title="Gossip Forum", domain="forum.net", url="https://forum.net/post/1", source_tier=SourceTier.COMMUNITY)
    s_rumor2 = Source(id="s-rumor2", title="Social Media Thread", domain="social.org", url="https://social.org/thread/2", source_tier=SourceTier.COMMUNITY)
    
    # Official source directly refutes
    ev_refute = Evidence(
        id="e-refute", source_id="s-police", claim_id="c-adv-10",
        exact_quote="Police confirmed the celebrity is alive and rumors of a fatal crash are completely false.",
        directness=EvidenceDirectness.DIRECT,
        supports_claim=False,
        contradicts_claim=True,
        scope_match=True
    )
    # Community sources claim it's true
    ev_rumor1 = Evidence(
        id="e-r1", source_id="s-rumor1", claim_id="c-adv-10",
        exact_quote="Celebrity died in a tragic crash yesterday afternoon.",
        directness=EvidenceDirectness.DIRECT,
        supports_claim=True,
        scope_match=True
    )
    ev_rumor2 = Evidence(
        id="e-r2", source_id="s-rumor2", claim_id="c-adv-10",
        exact_quote="Witnesses on forum claim the fatal accident took place.",
        directness=EvidenceDirectness.DIRECT,
        supports_claim=True,
        scope_match=True
    )
    
    assessment = assess_evidence_for_claim(claim, [s_police, s_rumor1, s_rumor2], [ev_refute, ev_rumor1, ev_rumor2], [])
    assert assessment.has_credible_contradicting_evidence is True
    
    verdict = compute_evidence_state(assessment, Verifiability.PUBLICLY_VERIFIABLE)
    assert verdict in (EvidenceState.UNSUPPORTED, EvidenceState.CONFLICTING)
    assert verdict != EvidenceState.SUFFICIENT


def test_adversarial_11_boilerplate_and_nav_links_cannot_act_as_evidence():
    """
    Invariant 11 (DOM Role Admissibility Filter):
    Scraped text containing navigation headers ('Login', 'Home', 'Privacy Policy')
    or speculative questions ('Is the company going bankrupt?') tagged with
    NAVIGATION_OR_LINK or SPECULATION_OR_QUESTION must be completely stripped of
    evidentiary weight (supports_claim forced to False).
    """
    from app.models.verification_models import EvidenceRole
    
    claim = make_test_claim("c-adv-11", "Company released financial statements.")
    src = Source(id="s1", title="Homepage", domain="corp.com", url="https://corp.com", source_tier=SourceTier.OFFICIAL)
    
    ev_nav = Evidence(
        id="e-nav", source_id="s1", claim_id="c-adv-11",
        exact_quote="Click here to login or read financial statements.",
        directness=EvidenceDirectness.DIRECT,
        supports_claim=True,
        scope_match=True,
        evidence_role=EvidenceRole.NAVIGATION_OR_LINK,
        element_role="NAV"
    )
    
    assessment = assess_evidence_for_claim(claim, [src], [ev_nav], [])
    assert assessment.direct_supporting_origin_count == 0
    assert assessment.has_strong_independent_support is False
    verdict = compute_evidence_state(assessment, Verifiability.PUBLICLY_VERIFIABLE)
    assert verdict == EvidenceState.INSUFFICIENT


def test_adversarial_12_cyclic_provenance_graph_does_not_loop_infinitely():
    """
    Invariant 12 (Graph Cycle Immunity):
    Malicious or syndication circular reposts: S1 -> S2 -> S3 -> S1.
    The provenance resolver must detect the cycle, log a CyclicProvenanceWarning,
    and break cleanly without an infinite recursion or StackOverflow.
    """
    s1 = Source(id="s1", title="Site 1", domain="site1.com", url="https://site1.com/1", source_tier=SourceTier.COMMUNITY)
    s2 = Source(id="s2", title="Site 2", domain="site2.com", url="https://site2.com/2", source_tier=SourceTier.COMMUNITY)
    s3 = Source(id="s3", title="Site 3", domain="site3.com", url="https://site3.com/3", source_tier=SourceTier.COMMUNITY)
    
    sources = [s1, s2, s3]
    source_map = {s.id: s for s in sources}
    
    # Create cycle: s1 cites s2, s2 cites s3, s3 cites s1
    prov_map = {
        "s1": SourceProvenance(source_id="s1", origin_source_id="s2", provenance_type=ProvenanceType.CITES),
        "s2": SourceProvenance(source_id="s2", origin_source_id="s3", provenance_type=ProvenanceType.CITES),
        "s3": SourceProvenance(source_id="s3", origin_source_id="s1", provenance_type=ProvenanceType.CITES)
    }
    
    origin = _resolve_ultimate_origin("s1", prov_map, source_map)
    assert origin in ("s1", "s2", "s3")  # Successfully breaks out cleanly


def test_adversarial_13_exact_quote_character_anchor_tamper_proofing():
    """
    Invariant 13 (Physical Anchor Tamper Resistance):
    An attacker modifies byte/character slices in the quote to insert an unauthorized claim.
    The WebScraper anchor resolver matches quotes against document text.
    If characters do not align with original document slice, it cannot be classified as EXACT.
    """
    scraper = WebScraper()
    full_text = "The quarterly gross revenue reached $12.5 million according to audited results."
    
    # Legitimate exact quote
    start, end, prefix, suffix, match_tier, element_role, block_id = scraper.locate_quote_spans(full_text, "$12.5 million")
    assert match_tier in ("EXACT", "NORMALIZED_EXACT")
    assert start is not None and start >= 0
    
    # Tampered quote where attacker changed million to billion
    t_start, t_end, t_pre, t_suf, t_match_tier, _, _ = scraper.locate_quote_spans(full_text, "$12.5 billion")
    assert t_match_tier == "UNVERIFIED"
    assert t_start is None
