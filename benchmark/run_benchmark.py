"""
AI Claim Verifier — Synthetic Rule Regression Benchmark Suite

Explicitly tests the deterministic rule engine logic, provenance de-duplication,
and state transition regression across gold boundary cases.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.models.verification_models import (
    Claim, Source, SourceTier, SourceProvenance, ProvenanceType,
    Evidence, EvidenceDirectness, EvidenceState, Verifiability, InputType
)
from app.engine.verdict_rules import (
    assess_evidence_for_claim, compute_evidence_state
)

# Unordered category labels for confusion matrix visualization display only
CONFUSION_MATRIX_LABELS = [
    "SUFFICIENT", "STRONG", "INSUFFICIENT", "CONFLICTING", "UNSUPPORTED", "NOT_ASSESSABLE"
]

def is_overclaim(pred: str, gold: str) -> bool:
    """
    Safety Violation Metric:
    Returns True if the system positively confirmed (SUFFICIENT or STRONG)
    a claim whose ground truth is UNSUPPORTED, INSUFFICIENT, CONFLICTING, or NOT_ASSESSABLE.
    """
    if gold in ("INSUFFICIENT", "UNSUPPORTED", "NOT_ASSESSABLE", "CONFLICTING"):
        return pred in ("STRONG", "SUFFICIENT")
    return False

def is_conservative_miss(pred: str, gold: str) -> bool:
    """
    Conservative Under-claim Metric:
    Returns True if ground truth was positively confirmed (SUFFICIENT or STRONG),
    but the system conservatively degraded to INSUFFICIENT or NOT_ASSESSABLE.
    """
    return gold in ("STRONG", "SUFFICIENT") and pred in ("INSUFFICIENT", "NOT_ASSESSABLE")


def run_rule_regression_benchmark():
    cases_path = Path(__file__).resolve().parent / "benchmark_cases.jsonl"
    with open(cases_path, "r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    print(f"============================================================")
    print(f" [BENCHMARK] Synthetic Rule Engine Regression (Cases: {len(cases)})")
    print(f"============================================================")

    correct_verdicts = 0
    total_cases = len(cases)
    overclaim_cases = 0
    conservative_miss_cases = 0
    confusion_matrix = defaultdict(lambda: defaultdict(int))

    for item in cases:
        c_id = item["id"]
        statement = item["claim"]
        gold_state = item["gold_state"]
        category = item.get("category", "")

        claim = Claim(
            id=c_id,
            original_input=statement,
            input_type=InputType.TEXT,
            statement=statement,
            claim_index=0,
            verifiability=Verifiability.NOT_PUBLICLY_VERIFIABLE if gold_state == "NOT_ASSESSABLE" else Verifiability.PUBLICLY_VERIFIABLE,
            verifiability_reason="Benchmark evaluation context",
            verified_as_of="2026-08-28"
        )

        sources = []
        evidences = []
        provenances = []

        if gold_state == "SUFFICIENT":
            sources = [
                Source(id="s-1", url="mock://official/news", domain="official.com", title="Official", source_tier=SourceTier.OFFICIAL),
                Source(id="s-2", url="mock://reuters/report", domain="reuters.com", title="Reuters", source_tier=SourceTier.AUTHORITATIVE)
            ]
            evidences = [
                Evidence(id="e-1", source_id="s-1", claim_id=c_id, exact_quote=statement, supports_claim=True, directness=EvidenceDirectness.DIRECT, scope_match=True),
                Evidence(id="e-2", source_id="s-2", claim_id=c_id, exact_quote=statement, supports_claim=True, directness=EvidenceDirectness.DIRECT, scope_match=True)
            ]
        elif gold_state == "STRONG":
            sources = [
                Source(id="s-1", url="mock://reuters/report", domain="reuters.com", title="Reuters", source_tier=SourceTier.AUTHORITATIVE),
                Source(id="s-2", url="mock://bloomberg/news", domain="bloomberg.com", title="Bloomberg", source_tier=SourceTier.AUTHORITATIVE)
            ]
            evidences = [
                Evidence(id="e-1", source_id="s-1", claim_id=c_id, exact_quote=statement, supports_claim=True, directness=EvidenceDirectness.DIRECT, scope_match=True),
                Evidence(id="e-2", source_id="s-2", claim_id=c_id, exact_quote=statement, supports_claim=True, directness=EvidenceDirectness.DIRECT, scope_match=True)
            ]
        elif gold_state == "CONFLICTING":
            sources = [
                Source(id="s-1", url="mock://caixin/news", domain="caixin.com", title="Caixin", source_tier=SourceTier.AUTHORITATIVE),
                Source(id="s-2", url="mock://reuters/report", domain="reuters.com", title="Reuters", source_tier=SourceTier.AUTHORITATIVE)
            ]
            evidences = [
                Evidence(id="e-1", source_id="s-1", claim_id=c_id, exact_quote=statement, supports_claim=True, directness=EvidenceDirectness.DIRECT, scope_match=True),
                Evidence(id="e-2", source_id="s-2", claim_id=c_id, exact_quote="数据审计显示并非该数额", contradicts_claim=True, directness=EvidenceDirectness.DIRECT, scope_match=True)
            ]
        elif gold_state == "UNSUPPORTED":
            sources = [
                Source(id="s-1", url="mock://sec/filing", domain="sec.gov", title="SEC", source_tier=SourceTier.OFFICIAL)
            ]
            evidences = [
                Evidence(id="e-1", source_id="s-1", claim_id=c_id, exact_quote="官方监管通告明确否定该事项", contradicts_claim=True, directness=EvidenceDirectness.DIRECT, scope_match=True)
            ]
        elif gold_state == "INSUFFICIENT":
            if category == "SYNDICATED_SINGLE_ORIGIN":
                sources = [Source(id=f"s-{i}", url=f"mock://blog{i}.com", domain=f"blog{i}.com", title=f"Blog {i}", source_tier=SourceTier.COMMUNITY) for i in range(10)]
                provenances = [SourceProvenance(source_id=f"s-{i}", origin_source_id="s-0", provenance_type=ProvenanceType.REPUBLISHES) for i in range(1, 10)]
                evidences = [Evidence(id=f"e-{i}", source_id=f"s-{i}", claim_id=c_id, exact_quote=statement, supports_claim=True, directness=EvidenceDirectness.INDIRECT, scope_match=True) for i in range(10)]
            elif category == "PRICE_VARIANT_DIFFERENCE":
                sources = [Source(id="s-1", url="mock://phone.com", domain="phone.com", title="Phone", source_tier=SourceTier.MAINSTREAM)]
                evidences = [Evidence(id="e-1", source_id="s-1", claim_id=c_id, exact_quote=statement, supports_claim=True, directness=EvidenceDirectness.CONTEXTUAL, scope_match=False)]
            else:
                sources = [Source(id="s-1", url="mock://reddit.com/r/tech", domain="reddit.com", title="Reddit", source_tier=SourceTier.COMMUNITY)]
                evidences = [Evidence(id="e-1", source_id="s-1", claim_id=c_id, exact_quote=statement, supports_claim=True, directness=EvidenceDirectness.INDIRECT, scope_match=True)]
        elif gold_state == "NOT_ASSESSABLE":
            sources = []
            evidences = []

        assessment = assess_evidence_for_claim(claim, sources, evidences, provenances)
        pred_state = compute_evidence_state(assessment, claim.verifiability)

        pred_val = pred_state.value
        confusion_matrix[gold_state][pred_val] += 1

        is_match = (pred_val == gold_state)
        if is_match:
            correct_verdicts += 1
        else:
            if is_overclaim(pred_val, gold_state):
                overclaim_cases += 1
            if is_conservative_miss(pred_val, gold_state):
                conservative_miss_cases += 1

        print(f"[{'PASS' if is_match else 'FAIL'}] {c_id}: {statement[:28]}... -> Pred: {pred_val} | Gold: {gold_state}")

    accuracy = (correct_verdicts / total_cases) * 100.0
    overclaim_rate = (overclaim_cases / total_cases) * 100.0
    miss_rate = (conservative_miss_cases / total_cases) * 100.0

    print(f"\n============================================================")
    print(f" [SUMMARY] SYNTHETIC RULE REGRESSION RESULTS")
    print(f" Total Cases Evaluated   : {total_cases}")
    print(f" Regression Passed       : {correct_verdicts} / {total_cases}")
    print(f" Exact State Accuracy    : {accuracy:.1f}%")
    print(f" Overclaim Rate (Safety) : {overclaim_rate:.1f}% ({overclaim_cases}/{total_cases})")
    print(f" Conservative Miss Rate  : {miss_rate:.1f}% ({conservative_miss_cases}/{total_cases})")
    print(f"============================================================")
    print(f" Confusion Matrix (Gold Rows x Pred Cols):")
    header = f"{'GOLD / PRED':<15}" + "".join([f"{s[:6]:>8}" for s in CONFUSION_MATRIX_LABELS])
    print(header)
    for g in CONFUSION_MATRIX_LABELS:
        row_str = f"{g:<15}"
        for p in CONFUSION_MATRIX_LABELS:
            row_str += f"{confusion_matrix[g][p]:>8}"
        print(row_str)
    print(f"============================================================\n")


if __name__ == "__main__":
    run_rule_regression_benchmark()
