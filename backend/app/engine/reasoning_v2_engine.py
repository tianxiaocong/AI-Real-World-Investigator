"""
AI Real-World Investigator — Evidence Reasoning V2 Engine

Implements deterministic evaluation of:
1. Multi-attribute compound slot fulfillment (solving rw-02/rw-04 slot disconnections)
2. Legitimate basis conflict arbitration (GAAP vs Non-GAAP, clinical trial phases) (solving rw-11/rw-13)
3. Authoritative denial vs rumor hierarchy (solving rw-14)
"""

from typing import List, Dict, Any, Optional, Set
from app.models.verification_models import (
    EvidenceState,
    SourceTier,
    Verifiability
)
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


def evaluate_compound_fact_fulfillment(
    fact_slots: FactSlots,
    relations: List[EvidenceRelation]
) -> ReasoningAssessmentV2:
    """
    Evaluates whether all required compound slots of a claim are satisfied
    by the extracted evidence relations.
    """
    assessment = ReasoningAssessmentV2()
    required_slots: Set[str] = {slot.slot_name for slot in fact_slots.compound_slots if slot.is_required}
    assessment.total_required_slots = len(required_slots)

    # Collect matched slots across supporting relations with acceptable scope
    fulfilled: Set[str] = set()
    for rel in relations:
        if rel.relation_type in (RelationType.DIRECT_SUPPORT, RelationType.INDIRECT_SUPPORT):
            if rel.scope_alignment in (ScopeAlignment.FULL_MATCH, ScopeAlignment.SUBSET_MATCH, ScopeAlignment.SUPERSET_MATCH):
                for slot in rel.matched_slots:
                    fulfilled.add(slot)

    assessment.fulfilled_slots = sorted(list(fulfilled))
    missing = required_slots - fulfilled
    assessment.missing_slots = sorted(list(missing))

    # Full compound support achieved if all required slots are fulfilled
    # (or if no compound slots were required, base assertion is supported)
    if not required_slots:
        assessment.has_full_compound_support = any(
            rel.relation_type == RelationType.DIRECT_SUPPORT for rel in relations
        )
    else:
        assessment.has_full_compound_support = len(missing) == 0

    # Count relation categories
    has_gaap = False
    has_non_gaap = False
    has_preliminary = False
    has_confirmed = False

    for rel in relations:
        if rel.relation_type == RelationType.DIRECT_SUPPORT:
            assessment.direct_support_sources += 1
        elif rel.relation_type == RelationType.QUALIFIED_CONFLICT:
            assessment.qualified_conflict_sources += 1
        elif rel.relation_type == RelationType.DIRECT_CONTRADICT:
            assessment.direct_contradiction_sources += 1
        elif rel.relation_type == RelationType.AUTHORITATIVE_REFUTE:
            assessment.authoritative_refute_sources += 1

        if rel.accounting_standard == AccountingStandard.GAAP:
            has_gaap = True
        elif rel.accounting_standard == AccountingStandard.NON_GAAP:
            has_non_gaap = True

        if rel.temporal_evolution == TemporalEvolution.PRELIMINARY:
            has_preliminary = True
        elif rel.temporal_evolution == TemporalEvolution.FINAL_CONFIRMED:
            has_confirmed = True

    # Detect legitimate basis duality
    if has_gaap and has_non_gaap:
        assessment.has_legitimate_duality = True
        assessment.duality_explanation = "Financial duality detected: Co-existence of GAAP and Non-GAAP metrics."
    elif has_preliminary and has_confirmed:
        assessment.has_legitimate_duality = True
        assessment.duality_explanation = "Clinical trial temporal evolution: Preliminary readout differs from confirmed final results."

    return assessment


def compute_reasoning_v2_verdict(
    fact_slots: FactSlots,
    relations: List[EvidenceRelation],
    source_tiers: List[SourceTier],
    verifiability: Verifiability = Verifiability.PUBLICLY_VERIFIABLE
) -> EvidenceState:
    """
    Computes the deterministic EvidenceState using Reasoning V2 IR:
    1. Pre-retrieval verifiability boundaries
    2. Authoritative refutation priority
    3. Legitimate basis & qualified conflict arbitration
    4. Multi-slot compound fulfillment & source independence thresholding
    """
    # 1. Verifiability Boundary Gate
    if verifiability in (Verifiability.HARD_TO_VERIFY, Verifiability.NOT_PUBLICLY_VERIFIABLE):
        return EvidenceState.NOT_ASSESSABLE

    assessment = evaluate_compound_fact_fulfillment(fact_slots, relations)

    # 2. Authoritative Refutation Priority (e.g. official denial in rw-14/rw-15)
    # If official source directly refutes and no official counter-support exists
    has_official_source = any(t == SourceTier.OFFICIAL for t in source_tiers)
    if assessment.authoritative_refute_sources > 0:
        # Check if there is an official direct counter-support
        has_official_support = any(
            t == SourceTier.OFFICIAL and r.relation_type == RelationType.DIRECT_SUPPORT
            for t, r in zip(source_tiers, relations)
        )
        if not has_official_support:
            return EvidenceState.UNSUPPORTED

    # 3. Conflict Arbitration (GAAP/Non-GAAP, Trial evolution, Direct contradictions)
    if assessment.has_legitimate_duality or assessment.qualified_conflict_sources > 0:
        return EvidenceState.CONFLICTING

    if assessment.direct_contradiction_sources > 0:
        if assessment.direct_support_sources > 0:
            return EvidenceState.CONFLICTING
        else:
            return EvidenceState.UNSUPPORTED

    # 4. Compound Multi-Attribute Support Thresholding
    if not assessment.has_full_compound_support:
        # Missing required attribute slots (e.g. price mentioned without storage in compound claim)
        return EvidenceState.INSUFFICIENT

    # 5. Independent Source Multi-Tier Thresholding
    num_supporting_sources = assessment.direct_support_sources
    if num_supporting_sources >= 2:
        if has_official_source:
            return EvidenceState.SUFFICIENT
        return EvidenceState.STRONG
    elif num_supporting_sources == 1:
        if has_official_source:
            return EvidenceState.SUFFICIENT
        return EvidenceState.INSUFFICIENT

    return EvidenceState.INSUFFICIENT
