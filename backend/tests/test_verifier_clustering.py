import pytest
from app.agents.verifier import VerificationAgent, ConflictJudgement
from app.models.schemas import ClaimType, VerificationStatus, ConfidenceLevel, SourceType
from app.providers.llm.mock_provider import MockLLMProvider

@pytest.mark.asyncio
async def test_verifier_merges_corroborated_claims_and_counts_independent_sources():
    mock_llm = MockLLMProvider()
    verifier = VerificationAgent(mock_llm)

    # Claim A from Reuters
    claim_a = {
        "statement": "公司于2024年完成10亿元B2轮融资，美团领投",
        "claim_type": ClaimType.FACT_STATEMENT,
        "confidence": ConfidenceLevel.HIGH,
        "exact_quote": "完成10亿元B2轮融资，美团领投",
        "source_id": "src-1",
        "source_url": "https://www.reuters.com/business/funding",
        "source_domain": "reuters.com",
        "source_title": "Reuters Report",
        "source_type": SourceType.NEWS,
        "credibility_score": 0.88,
        "embedding": await mock_llm.get_embedding("公司于2024年完成10亿元B2轮融资，美团领投")
    }

    # Claim B from Official Company site (asserting the same fact)
    claim_b = {
        "statement": "公司宣布完成10亿元B2轮融资，美团与深创投领投",
        "claim_type": ClaimType.FACT_STATEMENT,
        "confidence": ConfidenceLevel.HIGH,
        "exact_quote": "宣布完成10亿元B2轮融资，美团与深创投领投",
        "source_id": "src-2",
        "source_url": "https://www.company.com/press",
        "source_domain": "company.com",
        "source_title": "Official Announcement",
        "source_type": SourceType.OFFICIAL,
        "credibility_score": 0.95,
        "embedding": await mock_llm.get_embedding("公司于2024年完成10亿元B2轮融资，美团领投")
    }

    # Run clustering & verification
    results = await verifier.verify_and_cluster_claims([claim_a, claim_b])

    # Should be merged into 1 canonical claim
    assert len(results) == 1
    canonical = results[0]
    assert canonical["verification_status"] == "SUFFICIENT"
    assert canonical["evidence_state"] == "SUFFICIENT"
    assert canonical["independent_sources_count"] == 2
    assert len(canonical["sources"]) == 2
    assert "证据充分" in canonical["verdict_summary"]
    assert len(canonical["verdict_reasons"]) >= 2

@pytest.mark.asyncio
async def test_verifier_classifies_opinions():
    mock_llm = MockLLMProvider()
    verifier = VerificationAgent(mock_llm)

    opinion_claim = {
        "statement": "某分析师认为该公司具身模型在泛化性上落后于行业平均",
        "claim_type": ClaimType.OPINION,
        "confidence": ConfidenceLevel.MEDIUM,
        "exact_quote": "模型在泛化性上落后于行业平均",
        "source_id": "src-3",
        "source_url": "https://www.zhihu.com/question/123",
        "source_domain": "zhihu.com",
        "source_title": "知乎专栏分析",
        "source_type": SourceType.FORUM,
        "credibility_score": 0.50,
        "embedding": await mock_llm.get_embedding("某分析师认为该公司具身模型在泛化性上落后于行业平均")
    }

    results = await verifier.verify_and_cluster_claims([opinion_claim])
    assert len(results) == 1
    assert results[0]["verification_status"] == "NOT_ASSESSABLE"
    assert "无法评估" in results[0]["verdict_summary"]
