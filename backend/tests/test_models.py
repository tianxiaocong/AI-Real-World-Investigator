import pytest
from app.models.schemas import (
    ClaimType, VerificationStatus, ConfidenceLevel, SourceType,
    ClaimBase, EvidenceSnippetBase, ResearchPlan, TargetType, SubTask
)

def test_claim_model_validation():
    claim = ClaimBase(
        statement="Company X raised $15M in Series A",
        claim_type=ClaimType.FACT_STATEMENT,
        confidence=ConfidenceLevel.HIGH,
        verification_status=VerificationStatus.CONFIRMED,
        reasoning="Corroborated by TechCrunch and official filing.",
        verdict_summary="🟢 已确认 (2个独立信源)",
        verdict_reasons=["✓ 官方来源证实", "✓ 媒体独立印证"],
        independent_sources_count=2
    )
    assert claim.claim_type == "FACT_STATEMENT"
    assert claim.verification_status == "CONFIRMED"
    assert claim.confidence == "HIGH"
    assert claim.independent_sources_count == 2
    assert len(claim.verdict_reasons) == 2

def test_research_plan_schema():
    plan = ResearchPlan(
        target_type=TargetType.COMPANY,
        target_name="OpenAI",
        key_hypotheses=["High growth", "High compute cost"],
        sub_tasks=[
            SubTask(
                id="t-1",
                dimension="Financials",
                question="What is the revenue?",
                search_queries=["OpenAI revenue 2024"],
                rationale="Assess commercial model"
            )
        ]
    )
    assert len(plan.sub_tasks) == 1
    assert plan.target_type == TargetType.COMPANY
