import pytest
from app.models.verification_models import (
    Source,
    SourceTier,
    Claim,
    Verifiability,
    InputType,
    Evidence,
    EvidenceDirectness,
    EvidenceAssessment,
    EvidenceState,
    SourceProvenance,
    ProvenanceType
)
from app.services.verification_service import resolve_textual_provenance
from app.engine.verdict_rules import assess_evidence_for_claim, compute_evidence_state

def test_resolve_textual_provenance_intra_manifest_compound():
    sources = [
        Source(id="s-01", url="https://techdailynews.org/amazon-brainwave-acquisition", domain="techdailynews.org", title="TechDailyNews", source_tier=SourceTier.COMMUNITY),
        Source(id="s-02", url="https://siliconvalleyinsider.blog/amazon-buys-brainwave", domain="siliconvalleyinsider.blog", title="Silicon Valley Insider", source_tier=SourceTier.COMMUNITY)
    ]
    # S2 cites "TechDailyNews and @AILeaker"
    matched_id = resolve_textual_provenance("TechDailyNews and @AILeaker", sources)
    assert matched_id == "s-01"

def test_resolve_textual_provenance_external_handle_clustering():
    sources = [
        Source(id="s-01", url="https://techdailynews.org/amazon-brainwave-acquisition", domain="techdailynews.org", title="TechDailyNews", source_tier=SourceTier.COMMUNITY),
        Source(id="s-02", url="https://siliconvalleyinsider.blog/amazon-buys-brainwave", domain="siliconvalleyinsider.blog", title="Silicon Valley Insider", source_tier=SourceTier.COMMUNITY)
    ]
    # S1 cites external Twitter handle
    matched_id_s1 = resolve_textual_provenance("AILeaker tweet", sources)
    assert matched_id_s1 == "ext:aileaker"

def test_end_to_end_provenance_de_duplication_syndicated_rumor():
    sources = [
        Source(id="s-01", url="https://techdailynews.org/amazon-brainwave", domain="techdailynews.org", title="TechDailyNews", source_tier=SourceTier.COMMUNITY),
        Source(id="s-02", url="https://siliconvalleyinsider.blog/amazon-buys-brainwave", domain="siliconvalleyinsider.blog", title="Silicon Valley Insider", source_tier=SourceTier.COMMUNITY)
    ]
    evidences = [
        Evidence(id="e-01", claim_id="c-01", source_id="s-01", exact_quote="Acquired", supports_claim=True, directness=EvidenceDirectness.DIRECT),
        Evidence(id="e-02", claim_id="c-01", source_id="s-02", exact_quote="Acquired", supports_claim=True, directness=EvidenceDirectness.DIRECT)
    ]
    provenances = [
        SourceProvenance(source_id="s-01", origin_source_id="ext:aileaker", provenance_type=ProvenanceType.REPUBLISHES),
        SourceProvenance(source_id="s-02", origin_source_id="s-01", provenance_type=ProvenanceType.CITES)
    ]
    claim = Claim(id="c-01", original_input="Acquisition", input_type=InputType.TEXT, statement="Acquisition", claim_index=0, verifiability=Verifiability.PUBLICLY_VERIFIABLE, verifiability_reason="test", verified_as_of="2026-08-28")
    
    assessment = assess_evidence_for_claim(claim, sources, evidences, provenances)
    assert assessment.independent_source_count == 1
    assert assessment.republish_count == 2
    state = compute_evidence_state(assessment, Verifiability.PUBLICLY_VERIFIABLE)
    assert state == EvidenceState.INSUFFICIENT
