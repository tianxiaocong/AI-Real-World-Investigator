"""
AI Real-World Investigator — Unit Tests for Autonomous Evidence-Gap Investigation Loop
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.models.verification_models import (
    Claim,
    InputType,
    EvidenceState,
    SourceTier,
    EvidenceDirectness,
    Verifiability
)
from app.agents.fast_verifier import (
    FastClaimVerifierAgent,
    EvidenceExtractionBatch,
    RawExtractedEvidence
)


@pytest.mark.asyncio
async def test_gap_targeted_query_generation():
    """Test that gap planner generates focused query keywords."""
    mock_llm = MagicMock()
    mock_search = MagicMock()
    agent = FastClaimVerifierAgent(llm_provider=mock_llm, search_provider=mock_search)

    claim = Claim(
        id="c-1",
        statement="某公司完成数亿元融资",
        original_input="某公司完成数亿元融资",
        input_type=InputType.TEXT,
        claim_index=0,
        verifiability=Verifiability.PUBLICLY_VERIFIABLE,
        verifiability_reason="公开商业融资",
        verified_as_of="2026-08-30"
    )

    q1 = agent._generate_gap_targeted_query(claim, ["缺少企业官方公告证实"])
    assert "官方公告" in q1

    q2 = agent._generate_gap_targeted_query(claim, ["缺少SEC财务报表披露"])
    assert "SEC" in q2 or "10-Q" in q2

    q3 = agent._generate_gap_targeted_query(claim, ["缺少独立第三方媒体证实"])
    assert "Reuters" in q3 or "权威报道" in q3


@pytest.mark.asyncio
async def test_autonomous_loop_terminates_in_single_round_when_sufficient():
    """Test that if round 1 produces SUFFICIENT, round 2 is not triggered."""
    mock_llm = MagicMock()
    mock_search = MagicMock()

    # Search returns 2 official/authoritative sources
    search_item_1 = MagicMock(url="https://sec.gov/filing", title="Official SEC Filing", snippet="Confirmed $1B funding", domain="sec.gov", is_synthetic=True, published_date="2026-08-30")
    search_item_2 = MagicMock(url="https://reuters.com/news", title="Reuters News", snippet="Reuters independently confirmed $1B funding", domain="reuters.com", is_synthetic=True, published_date="2026-08-30")
    mock_search.search = AsyncMock(return_value=[search_item_1, search_item_2])

    mock_llm.generate_structured = AsyncMock(return_value=EvidenceExtractionBatch(
        evidences=[
            RawExtractedEvidence(exact_quote="Confirmed $1B funding", context="SEC filing", supports_claim=True, contradicts_claim=False, directness=EvidenceDirectness.DIRECT, scope_match=True),
            RawExtractedEvidence(exact_quote="Reuters independently confirmed $1B funding", context="Reuters", supports_claim=True, contradicts_claim=False, directness=EvidenceDirectness.DIRECT, scope_match=True)
        ]
    ))
    mock_llm.generate = AsyncMock(return_value='{"why_reasons": ["获得官方SEC直接证实"], "evidence_gaps": [], "next_step_advice": "已充分证实"}')

    agent = FastClaimVerifierAgent(llm_provider=mock_llm, search_provider=mock_search)
    claim = Claim(
        id="c-1",
        statement="某公司完成10亿美元融资",
        original_input="某公司完成10亿美元融资",
        input_type=InputType.TEXT,
        claim_index=0,
        verifiability=Verifiability.PUBLICLY_VERIFIABLE,
        verifiability_reason="商业融资",
        verified_as_of="2026-08-30"
    )

    verdict = await agent._verify_single_claim(claim, "2026-08-30")

    # Verify single-round execution
    assert verdict.evidence_state == EvidenceState.SUFFICIENT
    assert verdict.multi_round_audit is not None
    assert verdict.multi_round_audit["round_count"] == 1
    # Search was called exactly once
    assert mock_search.search.call_count == 1


@pytest.mark.asyncio
async def test_autonomous_loop_triggers_round_2_on_insufficient():
    """Test that if round 1 is INSUFFICIENT with gaps, round 2 is triggered automatically."""
    mock_llm = MagicMock()
    mock_search = MagicMock()

    # Round 1: Single forum post -> INSUFFICIENT
    item_r1 = MagicMock(url="https://forum.example/post", title="Forum Rumor", snippet="Someone says company raised $1B", domain="forum.example", is_synthetic=True, published_date="2026-08-30")
    # Round 2: Targeted search finds official announcement
    item_r2 = MagicMock(url="https://sec.gov/filing", title="Official SEC Announcement", snippet="Confirmed $1B official filing", domain="sec.gov", is_synthetic=True, published_date="2026-08-30")
    
    mock_search.search = AsyncMock(side_effect=[[item_r1], [item_r2]])

    # LLM returns evidence for Round 1 and Round 2
    mock_llm.generate_structured = AsyncMock(side_effect=[
        EvidenceExtractionBatch(evidences=[
            RawExtractedEvidence(exact_quote="Someone says company raised $1B", context="Forum", supports_claim=True, contradicts_claim=False, directness=EvidenceDirectness.INDIRECT, scope_match=True)
        ]),
        EvidenceExtractionBatch(evidences=[
            RawExtractedEvidence(exact_quote="Confirmed $1B official filing", context="SEC", supports_claim=True, contradicts_claim=False, directness=EvidenceDirectness.DIRECT, scope_match=True)
        ])
    ])
    # LLM explanations for Round 1 and Round 2
    mock_llm.generate = AsyncMock(side_effect=[
        '{"why_reasons": ["仅有单一论坛信息"], "evidence_gaps": ["缺少官方公告直接证实"], "next_step_advice": "需核实官方"}',
        '{"why_reasons": ["获得官方SEC直接证实"], "evidence_gaps": [], "next_step_advice": "已充分证实"}'
    ])

    agent = FastClaimVerifierAgent(llm_provider=mock_llm, search_provider=mock_search)
    claim = Claim(
        id="c-1",
        statement="某公司完成10亿美元融资",
        original_input="某公司完成10亿美元融资",
        input_type=InputType.TEXT,
        claim_index=0,
        verifiability=Verifiability.PUBLICLY_VERIFIABLE,
        verifiability_reason="商业融资",
        verified_as_of="2026-08-30"
    )

    verdict = await agent._verify_single_claim(claim, "2026-08-30")

    # Verify multi-round execution
    assert verdict.multi_round_audit is not None
    assert verdict.multi_round_audit["round_count"] == 2
    assert verdict.multi_round_audit["initial_state"] == "INSUFFICIENT"
    # Search was called twice (Round 1 + Round 2 gap search)
    assert mock_search.search.call_count == 2
