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


@pytest.mark.asyncio
async def test_no_evidence_does_not_become_support():
    """
    Regression Test 1: Sources without exact_quote MUST NOT fabricate supporting evidence.
    Must evaluate strictly as INSUFFICIENT with 0 supporting evidence.
    """
    mock_llm = MockLLMProvider()
    verifier = VerificationAgent(mock_llm)

    unsupported_claim = {
        "statement": "某公司发布了下一代量子计算处理器",
        "claim_type": ClaimType.FACT_STATEMENT,
        "confidence": ConfidenceLevel.LOW,
        "exact_quote": "",  # Empty quote (no evidence extracted)
        "source_id": "src-4",
        "source_url": "https://techcrunch.com/quantum",
        "source_domain": "techcrunch.com",
        "source_title": "Quantum Computing Rumors",
        "source_type": SourceType.NEWS,
        "credibility_score": 0.80,
        "embedding": await mock_llm.get_embedding("某公司发布了下一代量子计算处理器")
    }

    results = await verifier.verify_and_cluster_claims([unsupported_claim])
    assert len(results) == 1
    res = results[0]
    assert res["supporting_evidence_count"] == 0
    assert res["has_direct_support"] is False
    assert res["verification_status"] == "INSUFFICIENT"
    assert res["evidence_state"] == "INSUFFICIENT"


def test_domain_only_provenance_does_not_merge_same_domain_sources():
    """
    Regression Test 2: resolve_provenance_target must NOT match domain-only strings.
    A reference to 'nytimes.com' must not accidentally match 'nytimes.com/article-A'.
    """
    from app.models.verification_models import Source, SourceTier
    from app.engine.verdict_rules import resolve_provenance_target

    sources = [
        Source(id="s-01", url="https://www.nytimes.com/2024/01/article-a", domain="nytimes.com", title="Article A", source_tier=SourceTier.AUTHORITATIVE),
        Source(id="s-02", url="https://www.nytimes.com/2024/02/article-b", domain="nytimes.com", title="Article B", source_tier=SourceTier.AUTHORITATIVE)
    ]

    # Domain-only target MUST NOT match
    assert resolve_provenance_target("nytimes.com", sources) is None
    assert resolve_provenance_target("https://nytimes.com", sources) is None
    assert resolve_provenance_target("NYTimes", sources) is None

    # Exact source_id MUST match
    assert resolve_provenance_target("s-01", sources) == "s-01"
    assert resolve_provenance_target("s-02", sources) == "s-02"

    # Exact canonical URL MUST match
    assert resolve_provenance_target("https://www.nytimes.com/2024/01/article-a", sources) == "s-01"
    assert resolve_provenance_target("http://nytimes.com/2024/02/article-b/", sources) == "s-02"


@pytest.mark.asyncio
async def test_embedding_failure_does_not_return_zero_vector():
    """
    Regression Test 3: LLM providers without API key / on failure return [] instead of [0.0] * 768.
    """
    from app.providers.llm.openai_provider import OpenAICompatibleProvider
    from app.providers.llm.gemini_provider import GeminiProvider

    openai_p = OpenAICompatibleProvider(api_key="")
    gemini_p = GeminiProvider(api_key="")

    res_openai = await openai_p.get_embedding("test query")
    res_gemini = await gemini_p.get_embedding("test query")

    assert res_openai == []
    assert res_gemini == []
    assert res_openai != [0.0] * 768
    assert res_gemini != [0.0] * 768

