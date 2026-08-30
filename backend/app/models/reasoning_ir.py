"""
AI Real-World Investigator — Evidence Reasoning V2 Intermediate Representation (IR)

Defines standardized Pydantic models for semantic fact slots, multi-attribute constraints,
accounting basis duality, clinical trial temporal evolution, and high-order evidence relations.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class RelationType(str, Enum):
    DIRECT_SUPPORT = "DIRECT_SUPPORT"              # Complete direct corroboration of all required fact slots
    INDIRECT_SUPPORT = "INDIRECT_SUPPORT"          # Secondary / transferred corroboration (e.g. contextual or partial)
    QUALIFIED_CONFLICT = "QUALIFIED_CONFLICT"      # Legitimate duality / accounting basis / trial phase evolution
    DIRECT_CONTRADICT = "DIRECT_CONTRADICT"        # Substantive factual or numerical contradiction
    AUTHORITATIVE_REFUTE = "AUTHORITATIVE_REFUTE"  # Explicit official denial / warning letter / regulatory refutation
    CONTEXTUAL = "CONTEXTUAL"                      # Background context, neither directly proves nor disproves


class AccountingStandard(str, Enum):
    GAAP = "GAAP"
    NON_GAAP = "NON_GAAP"
    ADJUSTED = "ADJUSTED"
    STATUTORY = "STATUTORY"
    UNKNOWN = "UNKNOWN"


class TemporalEvolution(str, Enum):
    PRELIMINARY = "PRELIMINARY"                    # Early cohort, preliminary readout, unconfirmed interim
    FINAL_CONFIRMED = "FINAL_CONFIRMED"            # Full phase 3, peer-reviewed, audited final report
    HISTORICAL_SUPERSEDED = "HISTORICAL_SUPERSEDED"# Obsolete pricing, previous version specs
    CURRENT = "CURRENT"                            # Current prevailing factual status


class ScopeAlignment(str, Enum):
    FULL_MATCH = "FULL_MATCH"                      # All attributes, qualifiers, and conditions match
    SUBSET_MATCH = "SUBSET_MATCH"                  # Evidence addresses a sub-component or single tier
    SUPERSET_MATCH = "SUPERSET_MATCH"              # Evidence encompasses broader domain
    MISMATCH = "MISMATCH"                          # Scope, geography, or population mismatch


class CompoundFactSlot(BaseModel):
    """Represents a specific atomic attribute or numerical parameter within a compound claim."""
    slot_name: str = Field(description="Name of the slot, e.g. 'price', 'storage_capacity', 'lead_investor'")
    value: str = Field(description="Value string or numerical entity, e.g. '3499', '256GB', 'Meituan'")
    unit: Optional[str] = Field(default=None, description="Unit of measurement, e.g. 'USD', 'GB', 'RMB'")
    is_required: bool = Field(default=True, description="True if mandatory for compound claim validity")
    qualifier: Optional[str] = Field(default=None, description="Qualifier or prefix, e.g. 'starting_at', 'nearly'")


class FactSlots(BaseModel):
    """Represents a structured decomposition of a claim into semantic slots and domain qualifiers."""
    entity: str = Field(description="Primary subject entity, e.g. 'Apple Vision Pro', 'TechCorp'")
    predicate: str = Field(description="Core predicate or action, e.g. 'retail_spec_pricing', 'q3_net_income'")
    compound_slots: List[CompoundFactSlot] = Field(default_factory=list, description="List of multi-attribute slots")
    time_context: Optional[str] = Field(default=None, description="Time context, e.g. '2024', 'Q3 2024'")
    accounting_basis: AccountingStandard = Field(default=AccountingStandard.UNKNOWN, description="Accounting standard")
    trial_phase: Optional[str] = Field(default=None, description="Clinical trial phase if biomedical")
    polarity: bool = Field(default=True, description="Assertion polarity: True=affirmative, False=negative")


class EvidenceRelation(BaseModel):
    """Binds an extracted Evidence quote to a Claim's FactSlots with relation taxonomy."""
    relation_type: RelationType = Field(description="Evidentiary relation classification")
    scope_alignment: ScopeAlignment = Field(default=ScopeAlignment.FULL_MATCH, description="Scope alignment")
    accounting_standard: AccountingStandard = Field(default=AccountingStandard.UNKNOWN, description="Accounting basis of source")
    temporal_evolution: TemporalEvolution = Field(default=TemporalEvolution.CURRENT, description="Trial / temporal state")
    matched_slots: List[str] = Field(default_factory=list, description="Slot names verified by this quote")
    unmatched_slots: List[str] = Field(default_factory=list, description="Slot names not addressed or contradicted")
    polarity_reasoning: str = Field(default="", description="Justification of relation assignment")


class ReasoningAssessmentV2(BaseModel):
    """Telemetry and aggregation metrics computed by Reasoning V2 Engine."""
    total_required_slots: int = 0
    fulfilled_slots: List[str] = Field(default_factory=list)
    missing_slots: List[str] = Field(default_factory=list)
    has_full_compound_support: bool = False
    
    # Polarities and Duality Counts
    direct_support_sources: int = 0
    qualified_conflict_sources: int = 0
    direct_contradiction_sources: int = 0
    authoritative_refute_sources: int = 0
    
    has_legitimate_duality: bool = False
    duality_explanation: Optional[str] = None
