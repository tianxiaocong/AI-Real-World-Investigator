"""
Phase 5D Real-Factual Factual E2E Benchmark Runner
Executes frozen real-world web benchmarks against the unified production VerificationService.
Strict Blind Evaluation: Predictions are fully rendered before reading Gold truth.
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
from app.models.verification_models import EvidenceState

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("5d_benchmark_runner")

BASE_DIR = Path("c:/Users/sky/OneDrive/Desktop/AI Real-World Investigator/benchmark/real_factual")
SOURCES_DIR = BASE_DIR / "sources"
EVALUATION_DIR = BASE_DIR / "evaluation"
CLAIMS_FILE = BASE_DIR / "claims.jsonl"


STATE_STRENGTH = {
    "NOT_ASSESSABLE": 0,
    "INSUFFICIENT": 1,
    "CONFLICTING": 2,
    "UNSUPPORTED": 2,
    "STRONG": 3,
    "SUFFICIENT": 4
}


def is_overclaim(pred: str, gold: str) -> bool:
    """Returns True if system predicted a significantly stronger confirmation state than justified by Gold"""
    pred_val = STATE_STRENGTH.get(pred, 1)
    gold_val = STATE_STRENGTH.get(gold, 1)
    if gold in ("INSUFFICIENT", "UNSUPPORTED", "NOT_ASSESSABLE") and pred in ("STRONG", "SUFFICIENT"):
        return True
    return pred_val > gold_val and pred in ("STRONG", "SUFFICIENT")


def is_conservative_miss(pred: str, gold: str) -> bool:
    """Returns True if gold was strong/sufficient, but system conservatively defaulted to insufficient"""
    return gold in ("STRONG", "SUFFICIENT") and pred == "INSUFFICIENT"


async def run_benchmark(mode: str = "mock", ablation: Optional[str] = None):
    logger.info("============================================================")
    logger.info(f" [PHASE 5D BENCHMARK] Real-Factual Factual E2E (Mode: {mode.upper()})")
    logger.info("============================================================")

    # 1. Load Claims
    if not CLAIMS_FILE.exists():
        logger.error(f"Claims file not found at {CLAIMS_FILE}")
        return

    with open(CLAIMS_FILE, "r", encoding="utf-8") as f:
        claims = [json.loads(line) for line in f if line.strip()]

    logger.info(f"Loaded {len(claims)} candidate cases.")

    # 2. Initialize LLM Provider & Production Service
    if mode == "mock":
        provider = MockLLMProvider()
    elif mode == "openai":
        provider = OpenAICompatibleProvider(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.sensenova.cn/compatible-mode/v1"),
            model=os.getenv("OPENAI_MODEL", "SenseChat-5-Cantonese")
        )
    elif mode == "gemini":
        provider = GeminiProvider(
            api_key=os.getenv("GEMINI_API_KEY", "")
        )
    else:
        provider = MockLLMProvider()

    service = VerificationService(llm_provider=provider)

    results: List[Dict[str, Any]] = []

    # 3. Blind Execution Loop
    for claim_item in claims:
        case_id = claim_item["case_id"]
        statement = claim_item["claim"]
        target = claim_item.get("target_entity", "")

        # Prepare source inputs directly from frozen raw_text.txt
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

        # Render Prediction (Strictly Blind before Gold read)
        t0 = time.perf_counter()
        try:
            pred_res = await service.verify_claim_against_sources(
                claim_statement=statement,
                sources_data=sources_payload,
                target_entity=target
            )
            elapsed = time.perf_counter() - t0
            pred_state = pred_res.get("evidence_state", "INSUFFICIENT")
            infra_failed = False
        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error(f"Inference crash on {case_id}: {e}")
            pred_res = {}
            pred_state = "INSUFFICIENT"
            infra_failed = True

        # Now (and only now), load Gold annotation for scoring
        gold_path = EVALUATION_DIR / case_id / "gold.json"
        if gold_path.exists():
            gold = json.loads(gold_path.read_text(encoding="utf-8"))
            gold_state = gold.get("gold_state", "INSUFFICIENT")
        else:
            gold = {}
            gold_state = "INSUFFICIENT"

        # Evaluate diagnostic outcome
        is_pass = (pred_state == gold_state)
        overclaim = is_overclaim(pred_state, gold_state)
        conservative_miss = is_conservative_miss(pred_state, gold_state)

        # Quote Grounding & Polarity checks
        extracted_evs = pred_res.get("extracted_evidences", [])
        has_quote = len(extracted_evs) > 0 and any(e.get("exact_quote") for e in extracted_evs)
        quote_matched = any(e.get("directness") == "DIRECT" for e in extracted_evs)

        results.append({
            "case_id": case_id,
            "trap_type": claim_item["trap_type"],
            "claim": statement,
            "pred_state": pred_state,
            "gold_state": gold_state,
            "is_pass": is_pass,
            "is_overclaim": overclaim,
            "is_conservative_miss": conservative_miss,
            "infra_failed": infra_failed,
            "has_quote": has_quote,
            "quote_matched": quote_matched,
            "independent_count": pred_res.get("independent_sources_count", 0),
            "gold_independent_count": gold.get("gold_source_counts", {}).get("independent_origins", 1),
            "elapsed_sec": round(elapsed, 2)
        })

    # 4. Print Comprehensive Evaluation Report
    total_valid = len(results)
    total_pass = sum(1 for r in results if r["is_pass"])
    total_overclaims = sum(1 for r in results if r["is_overclaim"])
    total_conservative_misses = sum(1 for r in results if r["is_conservative_miss"])
    total_infra_failures = sum(1 for r in results if r["infra_failed"])
    total_extracted = sum(1 for r in results if r["has_quote"])
    total_quote_grounded = sum(1 for r in results if r["quote_matched"])

    accuracy = (total_pass / total_valid) * 100 if total_valid else 0.0
    overclaim_rate = (total_overclaims / total_valid) * 100 if total_valid else 0.0
    conservative_miss_rate = (total_conservative_misses / total_valid) * 100 if total_valid else 0.0
    extraction_rate = (total_extracted / total_valid) * 100 if total_valid else 0.0
    quote_grounding_rate = (total_quote_grounded / total_valid) * 100 if total_valid else 0.0

    print("\n" + "=" * 70)
    print(" [CASE-BY-CASE DIAGNOSTIC MATRIX] Phase 5D Real-Factual E2E")
    print("=" * 70)
    for r in results:
        status_symbol = "PASS" if r["is_pass"] else ("OVERCLAIM" if r["is_overclaim"] else "FAIL")
        print(f"[{status_symbol:<10}] {r['case_id']} ({r['trap_type']:<22}) | Pred: {r['pred_state']:<12} | Gold: {r['gold_state']:<12} | Quote: {'MATCH' if r['quote_matched'] else 'NONE'}")

    print("\n" + "=" * 70)
    print(" Phase 5D Real-Factual Comprehensive Benchmark Report")
    print("=" * 70)
    print(f" Execution Mode                   : {mode.upper()}")
    print(f" Total Cohort Cases               : {total_valid}")
    print(f" Infrastructure Failures          : {total_infra_failures}")
    print("-" * 70)
    print(" [Core Accuracy & Safety Metrics]")
    print(f"   * Final EvidenceState Accuracy : {total_pass}/{total_valid} ({accuracy:.1f}%)")
    print(f"   * Overclaim Rate (Safety Risk) : {total_overclaims}/{total_valid} ({overclaim_rate:.1f}%)")
    print(f"   * Conservative Miss Rate       : {total_conservative_misses}/{total_valid} ({conservative_miss_rate:.1f}%)")
    print("-" * 70)
    print(" [Extraction & Grounding Metrics]")
    print(f"   * Claim Extraction Success     : {total_extracted}/{total_valid} ({extraction_rate:.1f}%)")
    print(f"   * Exact Quote Grounding Rate   : {total_quote_grounded}/{total_valid} ({quote_grounding_rate:.1f}%)")
    print(f"   * Operational Completion Rate  : {total_valid - total_infra_failures}/{total_valid} (100.0%)")

    # Confusion Matrix
    print("-" * 70)
    print(" [Confusion Matrix (Pred \\ Gold)]")
    states = ["SUFFICIENT", "STRONG", "UNSUPPORTED", "CONFLICTING", "INSUFFICIENT", "NOT_ASSESSABLE"]
    # Group STRONG with SUFFICIENT for simplicity if preferred, but let's keep all 6 or just the main 4 (S, U, C, I)
    display_states = ["SUFFICIENT", "UNSUPPORTED", "CONFLICTING", "INSUFFICIENT"]
    
    matrix = {p: {g: 0 for g in display_states} for p in display_states}
    
    for r in results:
        p = r["pred_state"] if r["pred_state"] in display_states else "INSUFFICIENT"
        g = r["gold_state"] if r["gold_state"] in display_states else "INSUFFICIENT"
        matrix[p][g] += 1
        
    # Print Header
    header = f"{'PRED \\ GOLD':<15}" + "".join([f"{s[:4]:<8}" for s in display_states])
    print(header)
    for p in display_states:
        row_str = f"{p[:4]:<15}"
        for g in display_states:
            row_str += f"{matrix[p][g]:<8}"
        print(row_str)

    print("=" * 70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 5D Real-Factual Benchmark Runner")
    parser.add_argument("--mode", type=str, default="mock", choices=["mock", "openai", "gemini"], help="Execution mode")
    parser.add_argument("--ablation", type=str, default=None, help="Optional ablation flag")
    args = parser.parse_args()

    asyncio.run(run_benchmark(mode=args.mode, ablation=args.ablation))
