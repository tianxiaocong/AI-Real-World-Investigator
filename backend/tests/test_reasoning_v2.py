"""
AI Real-World Investigator — Unit Test Suite for Evidence Reasoning V2 (IR & Engine)
"""

import pytest
from app.models.verification_models import EvidenceState, SourceTier, Verifiability
from app.models.reasoning_ir import (
    FactSlots,
    CompoundFactSlot,
    EvidenceRelation,
    RelationType,
    AccountingStandard,
    TemporalEvolution,
    ScopeAlignment,
    ReasoningAssessmentV2
)
from app.engine.reasoning_v2_engine import (
    evaluate_compound_fact_fulfillment,
    compute_reasoning_v2_verdict
)


def test_compound_slots_full_fulfillment():
    """Test compound claim with 2 required slots (price and storage) satisfied by evidence."""
    claim_slots = FactSlots(
        entity="Apple Vision Pro",
        predicate="retail_pricing_specs",
        compound_slots=[
            CompoundFactSlot(slot_name="price", value="3499", unit="USD", is_required=True),
            CompoundFactSlot(slot_name="storage", value="256GB", unit="GB", is_required=True)
        ]
    )

    # Evidence 1 confirms price, Evidence 2 confirms storage
    rel1 = EvidenceRelation(
        relation_type=RelationType.DIRECT_SUPPORT,
        scope_alignment=ScopeAlignment.FULL_MATCH,
        matched_slots=["price"]
    )
    rel2 = EvidenceRelation(
        relation_type=RelationType.DIRECT_SUPPORT,
        scope_alignment=ScopeAlignment.FULL_MATCH,
        matched_slots=["storage"]
    )

    assessment = evaluate_compound_fact_fulfillment(claim_slots, [rel1, rel2])
    assert assessment.has_full_compound_support is True
    assert set(assessment.fulfilled_slots) == {"price", "storage"}
    assert len(assessment.missing_slots) == 0


def test_compound_slots_missing_mandatory_slot_yields_insufficient():
    """Test that if a required slot is missing, verdict conservatively collapses to INSUFFICIENT."""
    claim_slots = FactSlots(
        entity="Apple Vision Pro",
        predicate="retail_pricing_specs",
        compound_slots=[
            CompoundFactSlot(slot_name="price", value="3499", unit="USD", is_required=True),
            CompoundFactSlot(slot_name="storage", value="256GB", unit="GB", is_required=True)
        ]
    )

    # Evidence only confirms price ($3,499) but says nothing about 256GB storage
    rel1 = EvidenceRelation(
        relation_type=RelationType.DIRECT_SUPPORT,
        scope_alignment=ScopeAlignment.FULL_MATCH,
        matched_slots=["price"]
    )

    verdict = compute_reasoning_v2_verdict(
        fact_slots=claim_slots,
        relations=[rel1],
        source_tiers=[SourceTier.MAINSTREAM]
    )
    assert verdict == EvidenceState.INSUFFICIENT


def test_accounting_standard_duality_resolves_to_conflicting():
    """Test GAAP vs Non-GAAP legitimate basis divergence resolves to CONFLICTING."""
    claim_slots = FactSlots(
        entity="TechCorp",
        predicate="q3_net_income",
        compound_slots=[
            CompoundFactSlot(slot_name="net_income", value="500", unit="million_usd", is_required=True)
        ]
    )

    # Source 1 (FT) reports Non-GAAP $500M support
    rel_non_gaap = EvidenceRelation(
        relation_type=RelationType.DIRECT_SUPPORT,
        accounting_standard=AccountingStandard.NON_GAAP,
        matched_slots=["net_income"]
    )
    # Source 2 (SEC 10-Q) reports GAAP $320M
    rel_gaap = EvidenceRelation(
        relation_type=RelationType.QUALIFIED_CONFLICT,
        accounting_standard=AccountingStandard.GAAP,
        matched_slots=["net_income"],
        polarity_reasoning="SEC 10-Q reports GAAP net income of $320M."
    )

    verdict = compute_reasoning_v2_verdict(
        fact_slots=claim_slots,
        relations=[rel_non_gaap, rel_gaap],
        source_tiers=[SourceTier.AUTHORITATIVE, SourceTier.OFFICIAL]
    )
    assert verdict == EvidenceState.CONFLICTING


def test_clinical_trial_temporal_duality_resolves_to_conflicting():
    """Test preliminary readout (85%) vs confirmed final trial (42%) resolves to CONFLICTING."""
    claim_slots = FactSlots(
        entity="BioPharma Drug",
        predicate="clinical_trial_orr",
        compound_slots=[
            CompoundFactSlot(slot_name="orr_rate", value="85", unit="percentage", is_required=True)
        ]
    )

    rel_prelim = EvidenceRelation(
        relation_type=RelationType.DIRECT_SUPPORT,
        temporal_evolution=TemporalEvolution.PRELIMINARY,
        matched_slots=["orr_rate"]
    )
    rel_final = EvidenceRelation(
        relation_type=RelationType.QUALIFIED_CONFLICT,
        temporal_evolution=TemporalEvolution.FINAL_CONFIRMED,
        matched_slots=["orr_rate"],
        polarity_reasoning="Final Phase 3 confirmed trial reported 42% ORR."
    )

    verdict = compute_reasoning_v2_verdict(
        fact_slots=claim_slots,
        relations=[rel_prelim, rel_final],
        source_tiers=[SourceTier.INDUSTRY, SourceTier.AUTHORITATIVE]
    )
    assert verdict == EvidenceState.CONFLICTING


def test_authoritative_official_denial_resolves_to_unsupported():
    """Test authoritative official refutation (e.g. corporate press release) takes precedence over blog rumor."""
    claim_slots = FactSlots(
        entity="Global Retail Corp",
        predicate="corporate_layoffs",
        compound_slots=[
            CompoundFactSlot(slot_name="layoff_pct", value="20", unit="percentage", is_required=True)
        ]
    )

    # Blog rumor asserts layoffs
    rel_rumor = EvidenceRelation(
        relation_type=RelationType.INDIRECT_SUPPORT,
        matched_slots=["layoff_pct"]
    )
    # Corporate press release explicitly denies
    rel_denial = EvidenceRelation(
        relation_type=RelationType.AUTHORITATIVE_REFUTE,
        scope_alignment=ScopeAlignment.FULL_MATCH,
        polarity_reasoning="Company press release explicitly denies any planned corporate layoffs."
    )

    verdict = compute_reasoning_v2_verdict(
        fact_slots=claim_slots,
        relations=[rel_rumor, rel_denial],
        source_tiers=[SourceTier.COMMUNITY, SourceTier.OFFICIAL]
    )
    assert verdict == EvidenceState.UNSUPPORTED


def test_verifiability_boundary_resolves_to_not_assessable():
    """Test private matters and non-public deliberations strictly yield NOT_ASSESSABLE."""
    claim_slots = FactSlots(
        entity="Executive John Doe",
        predicate="private_real_estate_decision"
    )

    verdict = compute_reasoning_v2_verdict(
        fact_slots=claim_slots,
        relations=[],
        source_tiers=[],
        verifiability=Verifiability.NOT_PUBLICLY_VERIFIABLE
    )
    assert verdict == EvidenceState.NOT_ASSESSABLE
