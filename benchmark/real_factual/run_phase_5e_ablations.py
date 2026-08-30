"""
Phase 5E Controlled Component Ablation Study Runner
Executes frozen real-world web benchmarks across 4 experimental conditions:
- Control: Full Production System (95.0% reference)
- Ablation A: w/o Provenance Resolution (measures independent source deduplication)
- Ablation B: w/o Semantic Polarity Arbitration (measures negation / contradiction handling)
- Ablation C: w/o Relevant-Window Selection (measures noisy / long-document filtering)
"""

import os
import sys
import json
import time
import asyncio
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv
load_dotenv()

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.verification_service import VerificationService
from app.providers.llm.mock_provider import MockLLMProvider
from app.providers.llm.gemini_provider import GeminiProvider
from app.providers.llm.openai_provider import OpenAICompatibleProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("5e_ablation_runner")

BASE_DIR = Path(__file__).resolve().parent
SOURCES_DIR = BASE_DIR / "sources"
EVALUATION_DIR = BASE_DIR / "evaluation"
CLAIMS_FILE = BASE_DIR / "claims.jsonl"
RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True, parents=True)

STATE_STRENGTH = {
    "NOT_ASSESSABLE": 0,
    "INSUFFICIENT": 1,
    "CONFLICTING": 2,
    "UNSUPPORTED": 2,
    "STRONG": 3,
    "SUFFICIENT": 4
}


def is_overclaim(pred: str, gold: str) -> bool:
    """Returns True if system predicted a confirmed state (SUFFICIENT or STRONG) for an unverified/false/conflicting claim"""
    if gold in ("INSUFFICIENT", "UNSUPPORTED", "NOT_ASSESSABLE", "CONFLICTING") and pred in ("STRONG", "SUFFICIENT"):
        return True
    return False


def is_conservative_miss(pred: str, gold: str) -> bool:
    """Returns True if gold was strong/sufficient, but system conservatively defaulted to insufficient or not assessable"""
    return gold in ("STRONG", "SUFFICIENT") and pred in ("INSUFFICIENT", "NOT_ASSESSABLE")


ABLATION_CONFIGS = {
    "control": {
        "name": "Control (Full System)",
        "enable_provenance": True,
        "enable_polarity_arbitration": True,
        "enable_relevant_window": True,
        "description": "Full production pipeline with all components enabled."
    },
    "ablation_a": {
        "name": "Ablation A (w/o Provenance)",
        "enable_provenance": False,
        "enable_polarity_arbitration": True,
        "enable_relevant_window": True,
        "description": "Disables textual provenance resolution; extracted cited_reference is not linked into provenance edges."
    },
    "ablation_b": {
        "name": "Ablation B (w/o Polarity Arbitration)",
        "enable_provenance": True,
        "enable_polarity_arbitration": False,
        "enable_relevant_window": True,
        "description": "Disables secondary LLM semantic polarity arbitration; falls back to baseline string-containment matching."
    },
    "ablation_c": {
        "name": "Ablation C (w/o Relevant Window)",
        "enable_provenance": True,
        "enable_polarity_arbitration": True,
        "enable_relevant_window": False,
        "description": "Disables targeted relevant-window selection; falls back to legacy prefix truncation raw_text[:16000]."
    }
}


async def run_single_condition(
    condition_key: str,
    mode: str = "openai",
    force: bool = False
) -> Dict[str, Any]:
    cfg = ABLATION_CONFIGS[condition_key]
    result_file = RESULTS_DIR / f"{condition_key}_{mode}.json"

    if result_file.exists() and not force:
        logger.info(f"Loading cached results for {condition_key} from {result_file}")
        with open(result_file, "r", encoding="utf-8") as f:
            return json.load(f)

    logger.info("=" * 70)
    logger.info(f" [PHASE 5E] Running Condition: {cfg['name']} (Mode: {mode.upper()})")
    logger.info(f" Description: {cfg['description']}")
    logger.info("=" * 70)

    # 1. Load Claims
    with open(CLAIMS_FILE, "r", encoding="utf-8") as f:
        claims = [json.loads(line) for line in f if line.strip()]

    # 2. Init LLM
    if mode == "mock":
        provider = MockLLMProvider()
    elif mode == "openai":
        provider = OpenAICompatibleProvider(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.sensenova.cn/compatible-mode/v1"),
            model=os.getenv("OPENAI_MODEL", "SenseChat-5-Cantonese")
        )
    elif mode == "gemini":
        provider = GeminiProvider(api_key=os.getenv("GEMINI_API_KEY", ""))
    else:
        provider = MockLLMProvider()

    service = VerificationService(llm_provider=provider)

    case_results: List[Dict[str, Any]] = []

    for claim_item in claims:
        case_id = claim_item["case_id"]
        statement = claim_item["claim"]
        target = claim_item.get("target_entity", "")

        case_sources_dir = SOURCES_DIR / case_id
        sources_payload = []

        for s_id in claim_item.get("sources", []):
            s_dir = case_sources_dir / s_id
            raw_text_path = s_dir / "raw_text.txt"
            meta_path = s_dir / "metadata.json"

            if not raw_text_path.exists() or not meta_path.exists():
                logger.warning(f"Missing fixture for {case_id}/{s_id}")
                continue

            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            raw_text = raw_text_path.read_text(encoding="utf-8")

            sources_payload.append({
                "source_id": s_id,
                "url": meta["source_url"],
                "domain": meta["domain"],
                "title": meta["title"],
                "raw_text": raw_text,
                "source_tier_hint": meta.get("source_tier_hint", "AUTHORITATIVE")
            })

        t0 = time.perf_counter()
        try:
            pred_res = await service.verify_claim_against_sources(
                claim_statement=statement,
                sources_data=sources_payload,
                target_entity=target,
                enable_provenance=cfg["enable_provenance"],
                enable_polarity_arbitration=cfg["enable_polarity_arbitration"],
                enable_relevant_window=cfg["enable_relevant_window"]
            )
            elapsed = time.perf_counter() - t0
            pred_state = pred_res.get("evidence_state", "INSUFFICIENT")
            infra_failed = False
        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error(f"Inference crash on {case_id} in {condition_key}: {e}")
            pred_res = {}
            pred_state = "INSUFFICIENT"
            infra_failed = True

        gold_path = EVALUATION_DIR / case_id / "gold.json"
        if gold_path.exists():
            gold = json.loads(gold_path.read_text(encoding="utf-8"))
            gold_state = gold.get("gold_state", "INSUFFICIENT")
        else:
            gold = {}
            gold_state = "INSUFFICIENT"

        is_pass = (pred_state == gold_state)
        overclaim = is_overclaim(pred_state, gold_state)
        conservative_miss = is_conservative_miss(pred_state, gold_state)

        extracted_evs = pred_res.get("extracted_evidences", [])
        has_quote = len(extracted_evs) > 0 and any(e.get("exact_quote") for e in extracted_evs)
        quote_matched = any(e.get("directness") == "DIRECT" for e in extracted_evs)

        evaluation_tag = "PASS" if is_pass else ("MODEL FAILURE / SAFE" if not overclaim else "MODEL FAILURE / OVERCLAIM")

        logger.info(f"[{cfg['name']}] Case {len(case_results)+1}/{len(claims)} ({case_id}) -> Pred: {pred_state:<12} | Gold: {gold_state:<12} | {evaluation_tag} ({elapsed:.1f}s)")

        case_results.append({
            "case_id": case_id,
            "trap_type": claim_item["trap_type"],
            "claim": statement,
            "target_entity": target,
            "pred_state": pred_state,
            "gold_state": gold_state,
            "is_pass": is_pass,
            "evaluation_tag": evaluation_tag,
            "is_overclaim": overclaim,
            "is_conservative_miss": conservative_miss,
            "infra_failed": infra_failed,
            "has_quote": has_quote,
            "quote_matched": quote_matched,
            "independent_count": pred_res.get("independent_sources_count", 0),
            "gold_independent_count": gold.get("gold_source_counts", {}).get("independent_origins", 1),
            "elapsed_sec": round(elapsed, 2)
        })

    # Summary Metrics
    total = len(case_results)
    pass_cnt = sum(1 for r in case_results if r["is_pass"])
    overclaim_cnt = sum(1 for r in case_results if r["is_overclaim"])
    miss_cnt = sum(1 for r in case_results if r["is_conservative_miss"])
    quote_cnt = sum(1 for r in case_results if r["quote_matched"])
    extract_cnt = sum(1 for r in case_results if r["has_quote"])
    infra_cnt = sum(1 for r in case_results if r["infra_failed"])

    summary = {
        "condition_key": condition_key,
        "condition_name": cfg["name"],
        "mode": mode,
        "total_cases": total,
        "accuracy": round((pass_cnt / total) * 100, 1) if total else 0.0,
        "accuracy_count": f"{pass_cnt}/{total}",
        "overclaim_rate": round((overclaim_cnt / total) * 100, 1) if total else 0.0,
        "overclaim_count": f"{overclaim_cnt}/{total}",
        "conservative_miss_rate": round((miss_cnt / total) * 100, 1) if total else 0.0,
        "conservative_miss_count": f"{miss_cnt}/{total}",
        "quote_grounding_rate": round((quote_cnt / total) * 100, 1) if total else 0.0,
        "quote_grounding_count": f"{quote_cnt}/{total}",
        "claim_extraction_rate": round((extract_cnt / total) * 100, 1) if total else 0.0,
        "infra_failures": infra_cnt,
        "cases": case_results
    }

    # Save to disk
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    return summary


def print_comparative_report(summaries: Dict[str, Dict[str, Any]]):
    print("\n" + "=" * 80)
    print(" [PHASE 5E: CONTROLLED COMPONENT ABLATION STUDY] FINAL COMPARISON")
    print("=" * 80)

    ctrl = summaries.get("control")
    ctrl_acc = ctrl["accuracy"] if ctrl else 95.0
    ctrl_oc = ctrl["overclaim_rate"] if ctrl else 0.0
    ctrl_qg = ctrl["quote_grounding_rate"] if ctrl else 100.0

    print(f"{'Condition':<32} | {'Accuracy':<14} | {'Overclaim':<12} | {'Quote Ground':<14} | {'Acc Delta':<10}")
    print("-" * 90)

    for k in ["control", "ablation_a", "ablation_b", "ablation_c"]:
        s = summaries.get(k)
        if not s:
            continue
        acc_str = f"{s['accuracy']:.1f}% ({s['accuracy_count']})"
        oc_str = f"{s['overclaim_rate']:.1f}% ({s['overclaim_count']})"
        qg_str = f"{s['quote_grounding_rate']:.1f}%"
        delta = s['accuracy'] - ctrl_acc
        delta_str = f"{delta:+.1f}%" if k != "control" else "Control Ref"

        print(f"{s['condition_name']:<32} | {acc_str:<14} | {oc_str:<12} | {qg_str:<14} | {delta_str:<10}")

    print("=" * 80)

    # Diagnostic Table for Priority Failure Modes
    priority_cases = ["p5d-05", "p5d-11", "p5d-12", "p5d-15", "p5d-16"]
    print("\n" + "-" * 80)
    print(" [KEY DIAGNOSTIC CASES ACROSS CONDITIONS]")
    print(f"{'Case ID':<8} | {'Gold State':<12} | {'Control':<12} | {'w/o Provenance':<14} | {'w/o Polarity':<14} | {'w/o Window':<12}")
    print("-" * 80)

    for cid in priority_cases:
        gold_st = "?"
        preds = {}
        for k in ["control", "ablation_a", "ablation_b", "ablation_c"]:
            s = summaries.get(k)
            if s:
                c_item = next((c for c in s["cases"] if c["case_id"] == cid), None)
                if c_item:
                    gold_st = c_item["gold_state"]
                    preds[k] = c_item["pred_state"]
                else:
                    preds[k] = "N/A"
            else:
                preds[k] = "TBD"

        print(f"{cid:<8} | {gold_st:<12} | {preds.get('control', 'N/A'):<12} | {preds.get('ablation_a', 'N/A'):<14} | {preds.get('ablation_b', 'N/A'):<14} | {preds.get('ablation_c', 'N/A'):<12}")

    print("=" * 80 + "\n")


async def main():
    parser = argparse.ArgumentParser(description="Phase 5E Controlled Component Ablation Study")
    parser.add_argument("--mode", type=str, default="openai", choices=["mock", "openai", "gemini"])
    parser.add_argument("--run", type=str, default="all", choices=["control", "ablation_a", "ablation_b", "ablation_c", "all"])
    parser.add_argument("--force", action="store_true", help="Re-run without using cached JSON")
    args = parser.parse_args()

    summaries = {}

    if args.run == "all":
        conditions_to_run = ["control", "ablation_a", "ablation_b", "ablation_c"]
    else:
        conditions_to_run = [args.run]

    for cond in conditions_to_run:
        summary = await run_single_condition(cond, mode=args.mode, force=args.force)
        summaries[cond] = summary

    # Load all existing summaries for printing comparison
    for k in ["control", "ablation_a", "ablation_b", "ablation_c"]:
        if k not in summaries:
            res_f = RESULTS_DIR / f"{k}_{args.mode}.json"
            if res_f.exists():
                with open(res_f, "r", encoding="utf-8") as f:
                    summaries[k] = json.load(f)

    print_comparative_report(summaries)


if __name__ == "__main__":
    asyncio.run(main())
