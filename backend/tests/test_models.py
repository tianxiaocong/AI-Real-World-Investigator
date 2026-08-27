import pytest
from app.models.schemas import (
    ClaimType, VerificationStatus, ConfidenceLevel, SourceType,
    ClaimBase, EvidenceSnippetBase, ResearchPlan, TargetType, SubTask
)

def test_claim_model_validation():
    claim = ClaimBase(
        statement="Company X raised $15M in Series A",
        claim_type=ClaimType.FACT,
        confidence=ConfidenceLevel.HIGH,
        verification_status=VerificationStatus.MULTI_SOURCE_SUPPORTED,
        reasoning="Corroborated by TechCrunch and official filing."
    )
    assert claim.claim_type == "FACT"
    assert claim.verification_status == "MULTI_SOURCE_SUPPORTED"
    assert claim.confidence == "HIGH"

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
