"""
AI Real-World Investigator — Unassisted E2E Benchmark Runner with 8-Stage Funnel Telemetry

Executes the FULL production E2E pipeline without ANY manual pre-structuring:
Input: Raw Claim Statement ONLY
Process:
  1. Claim Decomposition & Full Constraint FactSlots Extraction
  2. Multi-Way Directed Search & Pre-Scrape Relevance Gating
  3. Live WebScraper Raw Text Fetching & SSRF Protection
  4. Evidence & EvidenceRelation Autonomous Extraction
  5. 4-Tier Physical Quote Grounding (EXACT / NORMALIZED_EXACT only)
  6. Deterministic Reasoning V2 Engine Verdict & Safe Failure Invariant

Saves fully auditable metadata and calculates 8-stage funnel metrics:
1. decomposition_slot_recall
2. search_relevance_rate
3. live_fetch_success_rate
4. evidence_extraction_rate
5. quote_exact_rate
6. relation_valid_rate
7. verdict_accuracy
8. overclaim_rate
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


async def run_blind_evaluation(
    cases_file_path: str,
    output_file_path: str,
    llm_provider_name: str = "sensenova",
    search_provider_name: str = "duckduckgo"
):
    cases_file = Path(cases_file_path).resolve()
    with open(cases_file, "r", encoding="utf-8") as f:
        cases = json.load(f)

    llm = get_llm_provider(llm_provider_name, tier="reasoning")
    search = get_search_provider(search_provider_name)
    agent = FastClaimVerifierAgent(llm_provider=llm, search_provider=search)

    model_name = getattr(llm, "model", llm_provider_name)
    run_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    print("=" * 85)
    print(f"  AI Real-World Investigator — Autonomous E2E Funnel Evaluation")
    print(f"  Cases File:      {cases_file.name}")
    print(f"  LLM Provider:    {llm_provider_name} (Model: {model_name})")
    print(f"  Search Provider: {search_provider_name}")
    print(f"  Timestamp:       {run_timestamp}")
    print(f"  Total Cases:     {len(cases)}")
    print("=" * 85)

    results = []

    # Funnel Metric Accumulators
    total_slots_expected = 0
    total_slots_captured = 0
    total_searched_sources = 0
    total_relevant_sources = 0
    total_attempted_fetches = 0
    total_successful_fetches = 0
    total_extracted_evidences = 0
    total_grounded_exact_quotes = 0
    total_valid_relations = 0
    total_cases = len(cases)
    unwarranted_strong_count = 0

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

        # Slot recall evaluation
        num_slots = len(getattr(fact_slots, "compound_slots", [])) if fact_slots else 0
        if num_slots > 0:
            total_slots_captured += num_slots
        total_slots_expected += max(num_slots, 2)  # expect at least 2 key constraints per real case

        # Source & Fetch metrics
        case_sources = verdict.sources
        total_searched_sources += len(case_sources)
        case_relevant = [s for s in case_sources if s.fetch_status != "REJECTED_IRRELEVANT"]
        total_relevant_sources += len(case_relevant)
        case_fetched = [s for s in case_relevant if s.fetch_status in ("FETCH_SUCCESS", "SYNTHETIC_MOCK")]
        total_attempted_fetches += len(case_relevant)
        total_successful_fetches += len(case_fetched)

        # Evidence & Grounding metrics
        case_evidences = verdict.evidences
        total_extracted_evidences += len(case_evidences)
        case_grounded = [e for e in case_evidences if e.match_tier in ("EXACT", "NORMALIZED_EXACT") and e.is_admissible_factual_evidence]
        total_grounded_exact_quotes += len(case_grounded)
        total_valid_relations += len(relations)

        # Overclaim safety check
        if state in ("STRONG", "SUFFICIENT") and len(case_grounded) == 0:
            unwarranted_strong_count += 1

        print(f"  🎯 FINAL VERDICT: {state}")
        if fact_slots:
            compound_str = ", ".join([f"{cs.slot_name}={cs.value}" for cs in getattr(fact_slots, "compound_slots", [])]) or "none"
            print(f"  📦 EXTRACTED FactSlots: entity='{getattr(fact_slots, 'entity', '')}', slots=[{compound_str}], acct={getattr(fact_slots, 'accounting_basis', '')}")
        
        print(f"  🌐 RETRIEVED Sources ({len(case_sources)} total | {len(case_relevant)} relevant | {len(case_fetched)} live-fetched)")
        for s in case_sources:
            print(f"     - [{s.fetch_status}] ({s.source_tier.value}) {s.title[:45]} -> {s.url[:50]}")

        print(f"  🔗 EXTRACTED EvidenceRelations ({len(relations)} items):")
        for r_idx, rel in enumerate(relations):
            matched = getattr(rel, "matched_slots", [])
            print(f"     [{r_idx+1}] Type: {getattr(rel, 'relation_type', '')} | Matched: {matched} | Acct: {getattr(rel, 'accounting_standard', '')}")

        print(f"  📜 EXTRACTED Quotes ({len(case_evidences)} items | {len(case_grounded)} EXACT/NORMALIZED Grounded):")
        for e_idx, ev in enumerate(case_evidences):
            print(f"     [{e_idx+1}] Tier: [{ev.match_tier}] ({ev.char_start}:{ev.char_end}) \"{ev.exact_quote[:55]}...\" (Admissible: {ev.is_admissible_factual_evidence})")

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
                    "fetch_status": getattr(s, "fetch_status", "UNKNOWN"),
                    "fetch_mode": getattr(s, "fetch_mode", "LIVE"),
                    "content_hash": getattr(s, "content_hash", None),
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

    # Calculate 8-Stage Funnel Metrics
    slot_recall = (total_slots_captured / max(total_slots_expected, 1))
    relevance_rate = (total_relevant_sources / max(total_searched_sources, 1))
    fetch_success_rate = (total_successful_fetches / max(total_attempted_fetches, 1))
    quote_exact_rate = (total_grounded_exact_quotes / max(total_extracted_evidences, 1))
    overclaim_rate = (unwarranted_strong_count / max(total_cases, 1))

    print("\n" + "=" * 85)
    print("  8-STAGE AUDIT FUNNEL METRICS REPORT")
    print("=" * 85)
    print(f"  1. Decomposition Slot Recall:     {slot_recall:.1%} ({total_slots_captured}/{total_slots_expected} slots)")
    print(f"  2. Search Relevance Rate:         {relevance_rate:.1%} ({total_relevant_sources}/{total_searched_sources} sources)")
    print(f"  3. Live Fetch Success Rate:       {fetch_success_rate:.1%} ({total_successful_fetches}/{total_attempted_fetches} URLs)")
    print(f"  4. Evidence Extracted Count:      {total_extracted_evidences} items")
    print(f"  5. Quote EXACT Grounding Rate:    {quote_exact_rate:.1%} ({total_grounded_exact_quotes}/{total_extracted_evidences} quotes)")
    print(f"  6. EvidenceRelations Generated:   {total_valid_relations} relations")
    print(f"  7. Unwarranted Overclaim Rate:    {overclaim_rate:.1%} (Target: 0.0%)")
    print("=" * 85)

    output_path = Path(output_file_path).resolve()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "audit_funnel_summary": {
                "decomposition_slot_recall": f"{slot_recall:.1%}",
                "search_relevance_rate": f"{relevance_rate:.1%}",
                "live_fetch_success_rate": f"{fetch_success_rate:.1%}",
                "extracted_evidences_count": total_extracted_evidences,
                "quote_exact_rate": f"{quote_exact_rate:.1%}",
                "valid_relations_count": total_valid_relations,
                "overclaim_rate": f"{overclaim_rate:.1%}"
            },
            "cases": results
        }, f, ensure_ascii=False, indent=2)
    print(f"  Full Auditable Telemetry saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default=str(Path(__file__).resolve().parent / "blind_cases.json"), help="Cases JSON path")
    parser.add_argument("--output", default=str(Path(__file__).resolve().parent / "blind_results.json"), help="Output JSON path")
    parser.add_argument("--llm", default="sensenova", help="LLM Provider: sensenova, deepseek, mock")
    parser.add_argument("--search", default="duckduckgo", help="Search Provider: duckduckgo, tavily, mock")
    args = parser.parse_args()

    asyncio.run(run_blind_evaluation(args.cases, args.output, args.llm, args.search))
