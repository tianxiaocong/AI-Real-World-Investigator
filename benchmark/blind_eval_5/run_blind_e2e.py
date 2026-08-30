"""
AI Real-World Investigator — 5-Case Blind Unassisted E2E Benchmark Runner (v2 Full Audit Edition)

Executes the FULL production E2E pipeline without ANY manual pre-structuring:
Input: Raw Claim Statement ONLY
Process:
  1. Claim Decomposition & FactSlots Extraction (Autonomously by LLM)
  2. Web Search & Live/Raw Content Fetch
  3. Evidence & EvidenceRelation Extraction (Autonomously by LLM)
  4. Physical Raw-Text Quote Grounding & Provenance
  5. Deterministic Reasoning V2 Engine Verdict

Saves fully auditable metadata:
- LLM Provider & Model Name
- Search Provider
- Execution Timestamp & Hashes
- Character-Level Quote Placement Coordinates & Match Tiers
"""

import sys
import json
import asyncio
import datetime
import argparse
from pathlib import Path
from typing import List, Dict, Any

project_root = Path(__file__).resolve().parent.parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

# Enforce UTF-8 for Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from app.providers.llm import get_llm_provider
from app.providers.search import get_search_provider
from app.agents.fast_verifier import FastClaimVerifierAgent
from app.models.verification_models import InputType


async def run_blind_evaluation(llm_provider_name: str = "mock", search_provider_name: str = "mock"):
    cases_file = Path(__file__).resolve().parent / "blind_cases.json"
    with open(cases_file, "r", encoding="utf-8") as f:
        cases = json.load(f)

    llm = get_llm_provider(llm_provider_name, tier="reasoning")
    search = get_search_provider(search_provider_name)
    agent = FastClaimVerifierAgent(llm_provider=llm, search_provider=search)

    model_name = getattr(llm, "model", llm_provider_name)
    run_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    print("=" * 80)
    print(f"  AI Real-World Investigator: 5-Case Blind Unassisted E2E Evaluation")
    print(f"  LLM Provider:    {llm_provider_name} (Model: {model_name})")
    print(f"  Search Provider: {search_provider_name}")
    print(f"  Timestamp:       {run_timestamp}")
    print(f"  Total Cases:     {len(cases)}")
    print("=" * 80)

    results = []

    for idx, case in enumerate(cases):
        c_id = case["id"]
        domain = case["domain"]
        raw_claim = case["claim"]

        print(f"\n[{idx+1}/{len(cases)}] CASE: {c_id} ({domain})")
        print(f"  INPUT CLAIM: \"{raw_claim}\"")

        # EXECUTE UNASSISTED E2E PIPELINE
        coverage = await agent.verify_input(
            input_text=raw_claim,
            input_type=InputType.TEXT
        )

        verdict = coverage.verdicts[0] if coverage.verdicts else None
        if not verdict:
            print("  ❌ ERROR: No verdict produced.")
            continue

        fact_slots = verdict.fact_slots
        relations = verdict.relations
        state = verdict.evidence_state.value

        print(f"  🎯 FINAL VERDICT: {state}")
        if fact_slots:
            compound_str = ", ".join([f"{cs.slot_name}={cs.value}" for cs in getattr(fact_slots, "compound_slots", [])]) or "none"
            print(f"  📦 EXTRACTED FactSlots: entity='{getattr(fact_slots, 'entity', '')}', slots=[{compound_str}], acct={getattr(fact_slots, 'accounting_basis', '')}")
        
        print(f"  🔗 EXTRACTED EvidenceRelations ({len(relations)} items):")
        for r_idx, rel in enumerate(relations):
            matched = getattr(rel, "matched_slots", [])
            print(f"     [{r_idx+1}] Type: {getattr(rel, 'relation_type', '')} | Matched: {matched} | Acct: {getattr(rel, 'accounting_standard', '')}")

        print(f"  📜 EXTRACTED Quotes ({len(verdict.evidences)} items):")
        for e_idx, ev in enumerate(verdict.evidences):
            print(f"     [{e_idx+1}] Tier: [{ev.match_tier}] ({ev.char_start}:{ev.char_end}) \"{ev.exact_quote[:60]}...\" (Admissible: {ev.is_admissible_factual_evidence})")

        print(f"  💡 WHY REASONS:")
        for r in verdict.why_reasons:
            print(f"     {r}")

        # Record complete auditable case telemetry
        results.append({
            "id": c_id,
            "domain": domain,
            "claim": raw_claim,
            "execution_metadata": {
                "llm_provider": llm_provider_name,
                "model": model_name,
                "search_provider": search_provider_name,
                "timestamp": run_timestamp
            },
            "verdict_state": state,
            "fact_slots": fact_slots.model_dump() if hasattr(fact_slots, "model_dump") else str(fact_slots),
            "sources": [
                {
                    "id": s.id,
                    "url": s.url,
                    "domain": s.domain,
                    "source_tier": s.source_tier.value,
                    "is_synthetic": s.is_synthetic,
                    "raw_text_length": len(s.raw_text or "")
                }
                for s in verdict.sources
            ],
            "evidences": [
                {
                    "id": ev.id,
                    "source_id": ev.source_id,
                    "exact_quote": ev.exact_quote,
                    "char_start": ev.char_start,
                    "char_end": ev.char_end,
                    "match_tier": ev.match_tier,
                    "supports_claim": ev.supports_claim,
                    "contradicts_claim": ev.contradicts_claim,
                    "is_admissible": ev.is_admissible_factual_evidence
                }
                for ev in verdict.evidences
            ],
            "relations": [
                {
                    "relation_type": rel.relation_type.value,
                    "accounting_standard": rel.accounting_standard.value,
                    "temporal_evolution": rel.temporal_evolution.value,
                    "matched_slots": rel.matched_slots,
                    "polarity_reasoning": rel.polarity_reasoning
                }
                for rel in relations
            ],
            "why_reasons": verdict.why_reasons,
            "evidence_gaps": verdict.evidence_gaps
        })

    print("\n" + "=" * 80)
    print("  BLIND EVALUATION RUN COMPLETE.")
    print("=" * 80)

    output_path = Path(__file__).resolve().parent / "blind_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  Results saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm", default="mock", help="LLM Provider: mock, sensenova, deepseek")
    parser.add_argument("--search", default="mock", help="Search Provider: mock, duckduckgo, tavily")
    args = parser.parse_args()

    asyncio.run(run_blind_evaluation(args.llm, args.search))
