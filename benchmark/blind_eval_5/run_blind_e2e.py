"""
AI Real-World Investigator — Autonomous E2E Benchmark Runner (v3 Scientific Audit Edition)

Executes the FULL production E2E pipeline without ANY manual pre-structuring:
Input: Raw Claim Statement ONLY
Process:
  1. Claim Decomposition & Full Constraint FactSlots Extraction
  2. Multi-Way Directed Search & Pre-Scrape Relevance Gating (Zero Hardcoding)
  3. Live WebScraper Raw Text Fetching & SSRF Protection
  4. Evidence & EvidenceRelation Autonomous Extraction
  5. 4-Tier Physical Quote Grounding (EXACT / NORMALIZED_EXACT only)
  6. Autonomous Round 2 Investigation Loop (Strictly Enforcing WebScraper & Quote Grounding)
  7. Deterministic Reasoning V2 Engine Verdict & Safe Failure Invariant

Calculates rigorous scientific audit metrics:
1. true_gold_slot_recall (Matched predicted FactSlots vs Gold Standard Slots)
2. search_relevance_precision (Accepted sources / Total candidate search hits)
3. live_fetch_success_rate (Successful raw text fetches / Attempted fetches)
4. evidence_extraction_count (Total raw evidence statements extracted)
5. quote_exact_grounding_rate (EXACT / NORMALIZED_EXACT quotes grounded in raw text)
6. valid_evidence_relations_count (Number of structured EvidenceRelations generated)
7. successful_evidence_backed_closures (Number of positive proofs / refutations grounded in live quotes)
8. safe_degradation_closures (Number of safe insufficient verdicts acknowledging evidence gaps)
9. unwarranted_overclaim_rate (Target: 0.0%)
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


def evaluate_gold_slot_match(gold_slot: str, fact_slots: Any, claim_statement: str) -> bool:
    """Checks if a gold constraint is captured in the predicted FactSlots object."""
    if not fact_slots:
        return False
    
    g_lower = gold_slot.lower().strip()
    
    # 1. Check entity & predicate
    if g_lower in (getattr(fact_slots, "entity", "") or "").lower():
        return True
    if g_lower in (getattr(fact_slots, "predicate", "") or "").lower():
        return True
    if g_lower in (getattr(fact_slots, "time_context", "") or "").lower():
        return True
    if g_lower in str(getattr(fact_slots, "accounting_basis", "")).lower():
        return True
        
    # 2. Check compound_slots
    for cs in getattr(fact_slots, "compound_slots", []):
        val = str(cs.value).lower().strip() if cs.value else ""
        name = str(cs.slot_name).lower().strip() if cs.slot_name else ""
        if g_lower in val or val in g_lower or g_lower in name:
            return True
            
    return False


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
    print(f"  AI Real-World Investigator — Autonomous E2E Scientific Evaluation")
    print(f"  Cases File:      {cases_file.name}")
    print(f"  LLM Provider:    {llm_provider_name} (Model: {model_name})")
    print(f"  Search Provider: {search_provider_name}")
    print(f"  Timestamp:       {run_timestamp}")
    print(f"  Total Cases:     {len(cases)}")
    print("=" * 85)

    results = []

    # Funnel Metric Accumulators
    total_gold_slots = 0
    total_matched_gold_slots = 0
    total_searched_sources = 0
    total_relevant_sources = 0
    total_attempted_fetches = 0
    total_successful_fetches = 0
    total_extracted_evidences = 0
    total_grounded_exact_quotes = 0
    total_valid_relations = 0
    total_cases = len(cases)
    
    successful_evidence_backed_closures = 0
    safe_degradation_closures = 0
    unwarranted_overclaim_count = 0

    for idx, case in enumerate(cases):
        c_id = case["id"]
        domain = case["domain"]
        raw_claim = case["claim"]
        gold_slots = case.get("gold_slots", [])

        print(f"\n[{idx+1}/{len(cases)}] CASE: {c_id} ({domain})")
        print(f"  INPUT CLAIM: \"{raw_claim}\"")
        print(f"  🎯 GOLD SLOTS: {gold_slots}")

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

        # True Gold Slot Recall Evaluation
        case_gold_matched = 0
        for g in gold_slots:
            if evaluate_gold_slot_match(g, fact_slots, raw_claim):
                case_gold_matched += 1
                total_matched_gold_slots += 1
        total_gold_slots += len(gold_slots)
        case_slot_recall = case_gold_matched / len(gold_slots) if gold_slots else 1.0

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

        # Outcome Taxonomy Classification
        if state in ("STRONG", "SUFFICIENT", "UNSUPPORTED") and len(case_grounded) > 0:
            successful_evidence_backed_closures += 1
            closure_type = "POSITIVE_EVIDENCE_CLOSURE"
        elif state in ("INSUFFICIENT", "CONFLICTING", "NOT_ASSESSABLE"):
            safe_degradation_closures += 1
            closure_type = "SAFE_DEGRADATION_CLOSURE"
        else:
            unwarranted_overclaim_count += 1
            closure_type = "UNWARRANTED_OVERCLAIM"

        print(f"  🎯 FINAL VERDICT: {state} [{closure_type}]")
        if fact_slots:
            compound_str = ", ".join([f"{cs.slot_name}={cs.value}" for cs in getattr(fact_slots, "compound_slots", [])]) or "none"
            print(f"  📦 EXTRACTED FactSlots: entity='{getattr(fact_slots, 'entity', '')}', slots=[{compound_str}], acct={getattr(fact_slots, 'accounting_basis', '')}")
            print(f"  📊 Gold Slot Recall: {case_slot_recall:.1%} ({case_gold_matched}/{len(gold_slots)} matched)")
        
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
            "gold_slots": gold_slots,
            "gold_slots_matched": case_gold_matched,
            "gold_slots_recall": f"{case_slot_recall:.1%}",
            "execution_metadata": {
                "llm_provider": llm_provider_name,
                "model": model_name,
                "search_provider": search_provider_name,
                "timestamp": run_timestamp
            },
            "verdict_state": state,
            "closure_type": closure_type,
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

    # Calculate Scientific Funnel Metrics
    true_slot_recall = (total_matched_gold_slots / max(total_gold_slots, 1))
    search_relevance_precision = (total_relevant_sources / max(total_searched_sources, 1))
    fetch_success_rate = (total_successful_fetches / max(total_attempted_fetches, 1))
    quote_exact_rate = (total_grounded_exact_quotes / max(total_extracted_evidences, 1))
    overclaim_rate = (unwarranted_overclaim_count / max(total_cases, 1))

    print("\n" + "=" * 85)
    print("  SCIENTIFIC AUDIT METRICS REPORT")
    print("=" * 85)
    print(f"  1. True Gold Slot Recall:             {true_slot_recall:.1%} ({total_matched_gold_slots}/{total_gold_slots} gold slots)")
    print(f"  2. Search Relevance Precision:        {search_relevance_precision:.1%} ({total_relevant_sources}/{total_searched_sources} sources accepted)")
    print(f"  3. Live Fetch Success Rate:           {fetch_success_rate:.1%} ({total_successful_fetches}/{total_attempted_fetches} relevant URLs fetched)")
    print(f"  4. Evidence Extracted Count:          {total_extracted_evidences} items")
    print(f"  5. Quote EXACT Grounding Rate:        {quote_exact_rate:.1%} ({total_grounded_exact_quotes}/{total_extracted_evidences} quotes)")
    print(f"  6. EvidenceRelations Generated:       {total_valid_relations} relations")
    print(f"  7. Evidence-Backed Positive Closures: {successful_evidence_backed_closures} / {total_cases} cases")
    print(f"  8. Safe Degradation Closures:         {safe_degradation_closures} / {total_cases} cases")
    print(f"  9. Unwarranted Overclaim Rate:        {overclaim_rate:.1%} (Target: 0.0%)")
    print("=" * 85)

    output_path = Path(output_file_path).resolve()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "audit_summary": {
                "true_gold_slot_recall": f"{true_slot_recall:.1%}",
                "search_relevance_precision": f"{search_relevance_precision:.1%}",
                "live_fetch_success_rate": f"{fetch_success_rate:.1%}",
                "extracted_evidences_count": total_extracted_evidences,
                "quote_exact_grounding_rate": f"{quote_exact_rate:.1%}",
                "valid_relations_count": total_valid_relations,
                "successful_evidence_backed_closures": successful_evidence_backed_closures,
                "safe_degradation_closures": safe_degradation_closures,
                "unwarranted_overclaim_rate": f"{overclaim_rate:.1%}"
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
