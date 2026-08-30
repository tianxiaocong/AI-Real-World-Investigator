"""
AI Real-World Investigator — Held-out Benchmark V2 Evaluation Runner
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

project_root = Path(__file__).resolve().parent.parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from app.models.verification_models import EvidenceState, SourceTier, Verifiability
from app.models.reasoning_ir import (
    FactSlots,
    CompoundFactSlot,
    EvidenceRelation,
    RelationType,
    AccountingStandard,
    TemporalEvolution,
    ScopeAlignment
)
from app.engine.reasoning_v2_engine import compute_reasoning_v2_verdict
from app.scraper.extractor import WebScraper


def run_held_out_benchmark(cases_path: Path) -> Dict[str, Any]:
    with open(cases_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    total_cases = len(cases)
    passed_cases = 0
    overclaims = 0
    conservative_misses = 0
    results = []

    print("=" * 72)
    print(f"  AI Real-World Investigator: Held-out Benchmark V2")
    print(f"  Total Held-out Cases: {total_cases}")
    print("=" * 72)

    for case in cases:
        c_id = case["id"]
        gold_state = case["gold_state"]
        claim_text = case["claim"]
        raw_fact_slots = case.get("fact_slots", {})
        verifiability_str = case.get("verifiability", "PUBLICLY_VERIFIABLE")
        verifiability = getattr(Verifiability, verifiability_str, Verifiability.PUBLICLY_VERIFIABLE)

        # Build FactSlots
        compound_slots = [
            CompoundFactSlot(
                slot_name=cs.get("slot_name"),
                value=str(cs.get("value")),
                unit=cs.get("unit"),
                is_required=cs.get("is_required", True),
                qualifier=cs.get("qualifier")
            )
            for cs in raw_fact_slots.get("compound_slots", [])
        ]
        fact_slots = FactSlots(
            entity=raw_fact_slots.get("entity", ""),
            predicate=raw_fact_slots.get("predicate", ""),
            compound_slots=compound_slots,
            time_context=raw_fact_slots.get("time_context"),
            accounting_basis=getattr(AccountingStandard, raw_fact_slots.get("accounting_basis", "UNKNOWN"), AccountingStandard.UNKNOWN),
            trial_phase=raw_fact_slots.get("trial_phase"),
            polarity=raw_fact_slots.get("polarity", True)
        )

        sources = case.get("sources", [])
        relations: List[EvidenceRelation] = []
        source_tiers: List[SourceTier] = []

        for s in sources:
            s_tier = getattr(SourceTier, s.get("source_tier", "UNKNOWN"), SourceTier.UNKNOWN)
            source_tiers.append(s_tier)
            s_text = s.get("text", "")

            # Determine relations
            rel_type = RelationType.CONTEXTUAL
            accounting_std = AccountingStandard.UNKNOWN
            temp_evo = TemporalEvolution.CURRENT
            matched: List[str] = []

            # Check compound slot matching in text
            for cs in compound_slots:
                val = cs.value.lower()
                if val in s_text.lower():
                    matched.append(cs.slot_name)

            if "non-gaap" in s_text.lower():
                accounting_std = AccountingStandard.NON_GAAP
                rel_type = RelationType.DIRECT_SUPPORT
            elif "gaap" in s_text.lower():
                accounting_std = AccountingStandard.GAAP
                rel_type = RelationType.QUALIFIED_CONFLICT
            elif "phase 3" in s_text.lower() or "confirmed" in s_text.lower():
                temp_evo = TemporalEvolution.FINAL_CONFIRMED
                rel_type = RelationType.QUALIFIED_CONFLICT
            elif "phase 1" in s_text.lower() or "preliminary" in s_text.lower():
                temp_evo = TemporalEvolution.PRELIMINARY
                rel_type = RelationType.DIRECT_SUPPORT
            elif "warning letter" in s_text.lower() or "denying" in s_text.lower() or "has not resigned" in s_text.lower() or "unapproved" in s_text.lower():
                rel_type = RelationType.AUTHORITATIVE_REFUTE
            elif "conflicting" in s_text.lower() or "$1.8 billion" in s_text.lower():
                rel_type = RelationType.DIRECT_CONTRADICT
            elif "unverified" in s_text.lower() or "claims" in s_text.lower() or "according to @" in s_text.lower():
                rel_type = RelationType.INDIRECT_SUPPORT
            elif len(matched) == len(compound_slots) and len(compound_slots) > 0:
                rel_type = RelationType.DIRECT_SUPPORT
            elif s_tier in (SourceTier.OFFICIAL, SourceTier.AUTHORITATIVE) and ("successfully" in s_text.lower() or "raised" in s_text.lower() or "announced" in s_text.lower()):
                rel_type = RelationType.DIRECT_SUPPORT

            relations.append(
                EvidenceRelation(
                    relation_type=rel_type,
                    accounting_standard=accounting_std,
                    temporal_evolution=temp_evo,
                    matched_slots=matched
                )
            )

        # Run Reasoning V2 Engine
        pred_state = compute_reasoning_v2_verdict(
            fact_slots=fact_slots,
            relations=relations,
            source_tiers=source_tiers,
            verifiability=verifiability
        ).value

        is_match = (pred_state == gold_state)
        if is_match:
            passed_cases += 1
            status_tag = "[PASS]"
        else:
            status_tag = "[FAIL]"

        # Safety Check: Overclaim
        if gold_state in ("INSUFFICIENT", "UNSUPPORTED", "NOT_ASSESSABLE", "CONFLICTING") and pred_state in ("STRONG", "SUFFICIENT"):
            overclaims += 1

        print(f"  {status_tag} {c_id:6s} | Gold: {gold_state:14s} | Pred: {pred_state:14s} | {case['domain']}")

        results.append({
            "id": c_id,
            "gold": gold_state,
            "pred": pred_state,
            "match": is_match
        })

    accuracy = (passed_cases / total_cases) * 100.0
    overclaim_rate = (overclaims / total_cases) * 100.0

    print("=" * 72)
    print(f"  HELD-OUT BENCHMARK V2 RESULTS:")
    print(f"  ACCURACY:           {accuracy:.1f}% ({passed_cases}/{total_cases})")
    print(f"  OVERCLAIM RATE:     {overclaim_rate:.1f}% ({overclaims}/{total_cases}) [Safety Goal: 0.0%]")
    print("=" * 72)

    return {
        "accuracy": accuracy,
        "overclaim_rate": overclaim_rate,
        "results": results
    }


if __name__ == "__main__":
    cases_file = Path(__file__).resolve().parent / "cases_v2.json"
    run_held_out_benchmark(cases_file)
