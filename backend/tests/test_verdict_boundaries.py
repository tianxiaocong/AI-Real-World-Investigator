"""
AI Claim Verifier — 12 判定边界与整体覆盖测试 (v4 Final)
验证规则引擎在所有关键边界情况下的严格确定性判定行为。
"""

import pytest
from app.models.verification_models import (
    Claim,
    ClaimAttributes,
    Source,
    SourceTier,
    SourceProvenance,
    ProvenanceType,
    Evidence,
    EvidenceDirectness,
    EvidenceState,
    EvidenceAssessment,
    Verdict,
    OverallState,
    Verifiability,
    InputType
)
from app.engine.verdict_rules import (
    assess_evidence_for_claim,
    compute_evidence_state,
    compute_overall_state,
    generate_overall_coverage
)


@pytest.fixture
def base_claim():
    return Claim(
        id="c-1",
        original_input="测试公司完成10亿美元融资",
        input_type=InputType.TEXT,
        statement="测试公司完成10亿美元融资",
        claim_index=0,
        verifiability=Verifiability.PUBLICLY_VERIFIABLE,
        verifiability_reason="融资信息应有公开行业报道或企业披露",
        verified_as_of="2026-08-28"
    )


# Test 1: 两个独立可靠来源直接支持，无官方来源 → STRONG
def test_boundary_1_two_independent_sources_no_official(base_claim):
    src1 = Source(id="s-1", url="https://reuters.com/1", domain="reuters.com", title="Reuters", source_tier=SourceTier.AUTHORITATIVE)
    src2 = Source(id="s-2", url="https://bloomberg.com/2", domain="bloomberg.com", title="Bloomberg", source_tier=SourceTier.AUTHORITATIVE)
    
    ev1 = Evidence(id="e-1", source_id="s-1", claim_id="c-1", exact_quote="完成10亿美元融资", supports_claim=True, directness=EvidenceDirectness.DIRECT, scope_match=True)
    ev2 = Evidence(id="e-2", source_id="s-2", claim_id="c-1", exact_quote="获10亿美元投资", supports_claim=True, directness=EvidenceDirectness.DIRECT, scope_match=True)
    
    assessment = assess_evidence_for_claim(base_claim, [src1, src2], [ev1, ev2])
    state = compute_evidence_state(assessment, base_claim.verifiability)
    
    assert assessment.independent_source_count == 2
    assert state == EvidenceState.STRONG


# Test 2: 官方一手来源直接证实 + 另一独立来源直接支持 → SUFFICIENT
def test_boundary_2_official_plus_independent(base_claim):
    src_off = Source(id="s-off", url="https://company.com/news", domain="company.com", title="官方公告", source_tier=SourceTier.OFFICIAL)
    src_news = Source(id="s-news", url="https://reuters.com/1", domain="reuters.com", title="Reuters", source_tier=SourceTier.AUTHORITATIVE)
    
    ev_off = Evidence(id="e-off", source_id="s-off", claim_id="c-1", exact_quote="公司今日正式宣布完成10亿美元B轮融资", supports_claim=True, directness=EvidenceDirectness.DIRECT, scope_match=True)
    ev_news = Evidence(id="e-news", source_id="s-news", claim_id="c-1", exact_quote="公司完成10亿美元融资", supports_claim=True, directness=EvidenceDirectness.DIRECT, scope_match=True)
    
    assessment = assess_evidence_for_claim(base_claim, [src_off, src_news], [ev_off, ev_news])
    state = compute_evidence_state(assessment, base_claim.verifiability)
    
    assert assessment.has_supporting_official_source is True
    assert state == EvidenceState.SUFFICIENT


# Test 3: 10 个转载全部源自同一个原始来源 → 独立来源计数为 1，判定为 INSUFFICIENT
def test_boundary_3_ten_republishes_single_origin(base_claim):
    sources = [
        Source(id=f"s-{i}", url=f"https://blog{i}.com", domain=f"blog{i}.com", title=f"Blog {i}", source_tier=SourceTier.COMMUNITY)
        for i in range(10)
    ]
    provenances = [
        SourceProvenance(source_id=f"s-{i}", origin_source_id="s-0", provenance_type=ProvenanceType.REPUBLISHES)
        for i in range(1, 10)
    ]
    provenances.append(SourceProvenance(source_id="s-0", origin_source_id=None, provenance_type=ProvenanceType.ORIGINAL))
    
    evidences = [
        Evidence(id=f"e-{i}", source_id=f"s-{i}", claim_id="c-1", exact_quote="网传融资10亿", supports_claim=True, directness=EvidenceDirectness.DIRECT, scope_match=True)
        for i in range(10)
    ]
    
    assessment = assess_evidence_for_claim(base_claim, sources, evidences, provenances)
    state = compute_evidence_state(assessment, base_claim.verifiability)
    
    assert assessment.total_sources_found == 10
    assert assessment.independent_source_count == 1  # 经溯源去重后确认为 1 个独立源
    assert state == EvidenceState.INSUFFICIENT


# Test 4: 官方直接支持 + 权威媒体直接反驳 (均匹配范围) → CONFLICTING
def test_boundary_4_official_support_and_reuters_contradiction(base_claim):
    src_off = Source(id="s-off", url="https://company.com/news", domain="company.com", title="官方", source_tier=SourceTier.OFFICIAL)
    src_reu = Source(id="s-reu", url="https://reuters.com", domain="reuters.com", title="Reuters", source_tier=SourceTier.AUTHORITATIVE)
    
    ev_off = Evidence(id="e-off", source_id="s-off", claim_id="c-1", exact_quote="已完成10亿美元融资", supports_claim=True, directness=EvidenceDirectness.DIRECT, scope_match=True)
    ev_reu = Evidence(id="e-reu", source_id="s-reu", claim_id="c-1", exact_quote="投资方与审计证实实际融资仅2亿美元，10亿为夸大宣传", contradicts_claim=True, directness=EvidenceDirectness.DIRECT, scope_match=True)
    
    assessment = assess_evidence_for_claim(base_claim, [src_off, src_reu], [ev_off, ev_reu])
    state = compute_evidence_state(assessment, base_claim.verifiability)
    
    assert state == EvidenceState.CONFLICTING


# Test 5: 仅有单一 Reddit 社区源提及 → INSUFFICIENT
def test_boundary_5_single_reddit_source(base_claim):
    src = Source(id="s-red", url="https://reddit.com/r/tech", domain="reddit.com", title="Reddit", source_tier=SourceTier.COMMUNITY)
    ev = Evidence(id="e-red", source_id="s-red", claim_id="c-1", exact_quote="听说这家公司融了10亿", supports_claim=True, directness=EvidenceDirectness.INDIRECT, scope_match=True)
    
    assessment = assess_evidence_for_claim(base_claim, [src], [ev])
    state = compute_evidence_state(assessment, base_claim.verifiability)
    
    assert state == EvidenceState.INSUFFICIENT


# Test 6: 0 条证据，但该事实理论上公开可验证 → INSUFFICIENT (不是 UNSUPPORTED，也不是 NOT_ASSESSABLE)
def test_boundary_6_no_evidence_for_publicly_verifiable(base_claim):
    assessment = assess_evidence_for_claim(base_claim, [], [])
    state = compute_evidence_state(assessment, base_claim.verifiability)
    
    assert state == EvidenceState.INSUFFICIENT


# Test 7: 权威来源直接反驳且没有任何可靠直接支持 → UNSUPPORTED
def test_boundary_7_credible_contradiction_no_support(base_claim):
    src = Source(id="s-gov", url="https://sec.gov/filing", domain="sec.gov", title="SEC", source_tier=SourceTier.OFFICIAL)
    ev = Evidence(id="e-gov", source_id="s-gov", claim_id="c-1", exact_quote="监管披露记录显示该公司未进行任何10亿美元融资", contradicts_claim=True, directness=EvidenceDirectness.DIRECT, scope_match=True)
    
    assessment = assess_evidence_for_claim(base_claim, [src], [ev])
    state = compute_evidence_state(assessment, base_claim.verifiability)
    
    assert state == EvidenceState.UNSUPPORTED


# Test 8: 私人行为/未公开事项，0条证据 → NOT_ASSESSABLE
def test_boundary_8_private_matter_no_evidence():
    claim = Claim(
        id="c-priv",
        original_input="某CEO昨天晚上和朋友在北京吃了火锅",
        input_type=InputType.TEXT,
        statement="某CEO昨天晚上和朋友在北京吃了火锅",
        claim_index=0,
        verifiability=Verifiability.HARD_TO_VERIFY,
        verifiability_reason="私人行程通常不具备公开网络记录",
        verified_as_of="2026-08-28"
    )
    assessment = assess_evidence_for_claim(claim, [], [])
    state = compute_evidence_state(assessment, claim.verifiability)
    
    assert state == EvidenceState.NOT_ASSESSABLE


# Test 9: 官方来源虽然存在，但并未直接支持该 Claim (如范围不匹配) → INSUFFICIENT (防止'有官方来源就自动充分')
def test_boundary_9_official_source_scope_mismatch(base_claim):
    src_off = Source(id="s-off", url="https://company.com/annual", domain="company.com", title="官方年报", source_tier=SourceTier.OFFICIAL)
    # 官方年报谈论的是预计明年目标，而不是确认已融资10亿
    ev_off = Evidence(id="e-off", source_id="s-off", claim_id="c-1", exact_quote="公司预计未来将启动新一轮融资规划", supports_claim=False, directness=EvidenceDirectness.CONTEXTUAL, scope_match=False)
    
    assessment = assess_evidence_for_claim(base_claim, [src_off], [ev_off])
    state = compute_evidence_state(assessment, base_claim.verifiability)
    
    assert assessment.has_supporting_official_source is False
    assert state == EvidenceState.INSUFFICIENT


# Test 10: 10 个低质量独立源但均属于间接/背景提及 (非 DIRECT) → 不能自动升为 STRONG
def test_boundary_10_many_low_quality_indirect_sources(base_claim):
    sources = [
        Source(id=f"s-ind-{i}", url=f"https://forum{i}.com", domain=f"forum{i}.com", title=f"Forum {i}", source_tier=SourceTier.COMMUNITY)
        for i in range(5)
    ]
    evidences = [
        Evidence(id=f"e-ind-{i}", source_id=f"s-ind-{i}", claim_id="c-1", exact_quote="有人推测可能要融10亿", supports_claim=True, directness=EvidenceDirectness.INDIRECT, scope_match=True)
        for i in range(5)
    ]
    assessment = assess_evidence_for_claim(base_claim, sources, evidences)
    state = compute_evidence_state(assessment, base_claim.verifiability)
    
    assert assessment.has_strong_independent_support is False
    assert state == EvidenceState.INSUFFICIENT


# Test 11: 官方直接支持 + Reuters 独立直接反驳 (均 DIRECT 且 scope_match=True) → CONFLICTING
def test_boundary_11_direct_official_vs_direct_reuters(base_claim):
    src1 = Source(id="s-1", url="https://company.com", domain="company.com", title="公司", source_tier=SourceTier.OFFICIAL)
    src2 = Source(id="s-2", url="https://reuters.com", domain="reuters.com", title="Reuters", source_tier=SourceTier.AUTHORITATIVE)
    
    ev1 = Evidence(id="e-1", source_id="s-1", claim_id="c-1", exact_quote="融资10亿美元完全到账", supports_claim=True, directness=EvidenceDirectness.DIRECT, scope_match=True)
    ev2 = Evidence(id="e-2", source_id="s-2", claim_id="c-1", exact_quote="主权基金代表证实从未参与该轮10亿美元投资", contradicts_claim=True, directness=EvidenceDirectness.DIRECT, scope_match=True)
    
    assessment = assess_evidence_for_claim(base_claim, [src1, src2], [ev1, ev2])
    state = compute_evidence_state(assessment, base_claim.verifiability)
    
    assert state == EvidenceState.CONFLICTING


# Test 12: 支持证据仅为 Reddit 社区传闻，反驳证据为 Reuters 权威调查报道 → UNSUPPORTED (非对称质量不对冲)
def test_boundary_12_weak_support_versus_authoritative_contradiction(base_claim):
    src_red = Source(id="s-red", url="https://reddit.com", domain="reddit.com", title="Reddit", source_tier=SourceTier.COMMUNITY)
    src_reu = Source(id="s-reu", url="https://reuters.com", domain="reuters.com", title="Reuters", source_tier=SourceTier.AUTHORITATIVE)
    
    # 社区传言间接支持
    ev_red = Evidence(id="e-red", source_id="s-red", claim_id="c-1", exact_quote="帖子传言公司拿到大钱了", supports_claim=True, directness=EvidenceDirectness.INDIRECT, scope_match=True)
    # 权威媒体直接反证
    ev_reu = Evidence(id="e-reu", source_id="s-reu", claim_id="c-1", exact_quote="银行监管通报显示该公司破产清算，绝无10亿美元融资事实", contradicts_claim=True, directness=EvidenceDirectness.DIRECT, scope_match=True)
    
    assessment = assess_evidence_for_claim(base_claim, [src_red, src_reu], [ev_red, ev_reu])
    state = compute_evidence_state(assessment, base_claim.verifiability)
    
    assert assessment.has_direct_support is False
    assert assessment.has_credible_contradicting_evidence is True
    assert state == EvidenceState.UNSUPPORTED


# Test 13: 多 Claim 整体覆盖汇总 (OverallCoverage) 逻辑验证
def test_overall_coverage_logic():
    v1 = Verdict(claim_id="c-1", evidence_state=EvidenceState.SUFFICIENT, why_reasons=["官方证实"])
    v2 = Verdict(claim_id="c-2", evidence_state=EvidenceState.INSUFFICIENT, why_reasons=["暂无公开资料"])
    v3 = Verdict(claim_id="c-3", evidence_state=EvidenceState.CONFLICTING, why_reasons=["多方金额冲突"])
    
    coverage = generate_overall_coverage(
        original_input="公司2015年成立，获得10亿融资，并且已经实现盈利",
        input_type=InputType.TEXT,
        claims=[
            Claim(id="c-1", original_input="", input_type=InputType.TEXT, statement="公司2015年成立", claim_index=0, verifiability=Verifiability.PUBLICLY_VERIFIABLE, verifiability_reason="", verified_as_of="2026-08-28"),
            Claim(id="c-2", original_input="", input_type=InputType.TEXT, statement="获得10亿融资", claim_index=1, verifiability=Verifiability.PUBLICLY_VERIFIABLE, verifiability_reason="", verified_as_of="2026-08-28"),
            Claim(id="c-3", original_input="", input_type=InputType.TEXT, statement="已经实现盈利", claim_index=2, verifiability=Verifiability.PUBLICLY_VERIFIABLE, verifiability_reason="", verified_as_of="2026-08-28"),
        ],
        verdicts=[v1, v2, v3]
    )
    
    # 存在支持且存在冲突/不足 → MIXED，而非粗暴取最弱
    assert coverage.overall_state == OverallState.MIXED
    assert coverage.sufficient_count == 1
    assert coverage.insufficient_count == 1
    assert coverage.conflicting_count == 1
    assert "包含 3 个可验证事实点" in coverage.coverage_summary

def test_provenance_invariants():
    from app.engine.verdict_rules import _resolve_ultimate_origin
    
    # 1. Same domain != same origin
    s1 = Source(id="s1", url="http://nyt.com/1", domain="nyt.com", title="", source_tier=SourceTier.MAINSTREAM)
    s2 = Source(id="s2", url="http://nyt.com/2", domain="nyt.com", title="", source_tier=SourceTier.MAINSTREAM)
    source_map = {"s1": s1, "s2": s2}
    provenance_map = {}
    
    assert _resolve_ultimate_origin("s1", provenance_map, source_map) == "s1"
    assert _resolve_ultimate_origin("s2", provenance_map, source_map) == "s2"
    
    # 2. Different URL = dependent origin WHEN explicit republication exists
    s3 = Source(id="s3", url="http://other.com", domain="other.com", title="", source_tier=SourceTier.MAINSTREAM)
    source_map["s3"] = s3
    provenance_map["s3"] = SourceProvenance(source_id="s3", origin_source_id="s1", provenance_type=ProvenanceType.REPUBLISHES)
    
    assert _resolve_ultimate_origin("s3", provenance_map, source_map) == "s1"
    
    # 3. Cyclic provenance must trigger defensive isolation
    provenance_map["s1"] = SourceProvenance(source_id="s1", origin_source_id="s2", provenance_type=ProvenanceType.CITES)
    provenance_map["s2"] = SourceProvenance(source_id="s2", origin_source_id="s1", provenance_type=ProvenanceType.CITES)
    
    # Resolving s1 should detect cycle and isolate to s1
    resolved = _resolve_ultimate_origin("s1", provenance_map, source_map)
    assert resolved == "s1"


# Test 14: 限定性范围反驳 (Scope Restriction: 仅限兽用 vs 已获批用于人体) → CONFLICTING / CONTRADICTION
def test_boundary_14_scope_restriction_contradicts():
    claim = Claim(
        id="c-fda",
        original_input="该新药已获批用于人体临床治疗",
        input_type=InputType.TEXT,
        statement="该新药已获批用于人体临床治疗",
        claim_index=0,
        verifiability=Verifiability.PUBLICLY_VERIFIABLE,
        verifiability_reason="新药审批情况具备官方公开记录",
        verified_as_of="2026-08-28"
    )
    src_fda = Source(id="s-fda", url="https://fda.gov/news", domain="fda.gov", title="FDA", source_tier=SourceTier.OFFICIAL)
    
    # 证据显式说明严格仅限动物模型，直接构成对人体获批主张的反驳
    ev_fda = Evidence(
        id="e-fda",
        source_id="s-fda",
        claim_id="c-fda",
        exact_quote="该药目前严格仅限兽医动物模型研究，绝未获准用于人体临床试验或治疗",
        supports_claim=False,
        contradicts_claim=True,
        directness=EvidenceDirectness.DIRECT,
        scope_match=True
    )
    
    assessment = assess_evidence_for_claim(claim, [src_fda], [ev_fda])
    state = compute_evidence_state(assessment, claim.verifiability)
    
    assert assessment.has_credible_contradicting_evidence is True
    assert assessment.has_direct_support is False
    assert state == EvidenceState.UNSUPPORTED or state == EvidenceState.CONFLICTING


# Test 15: 否定性辟谣反驳 (Explicit Denial: 明确否认辞职 vs CEO已辞职) → CONFLICTING / CONTRADICTION
def test_boundary_15_explicit_denial_contradicts():
    claim = Claim(
        id="c-ceo",
        original_input="公司首席执行官已正式确认辞职",
        input_type=InputType.TEXT,
        statement="公司首席执行官已正式确认辞职",
        claim_index=0,
        verifiability=Verifiability.PUBLICLY_VERIFIABLE,
        verifiability_reason="高管任免属于公开事实",
        verified_as_of="2026-08-28"
    )
    src_corp = Source(id="s-corp", url="https://company.com/press", domain="company.com", title="Company Press", source_tier=SourceTier.OFFICIAL)
    
    # 官方发言人明确辟谣，构成直接反驳
    ev_corp = Evidence(
        id="e-corp",
        source_id="s-corp",
        claim_id="c-ceo",
        exact_quote="董事会与首席执行官本人已明确否认离职传闻，确认其将继续留任",
        supports_claim=False,
        contradicts_claim=True,
        directness=EvidenceDirectness.DIRECT,
        scope_match=True
    )
    
    assessment = assess_evidence_for_claim(claim, [src_corp], [ev_corp])
    state = compute_evidence_state(assessment, claim.verifiability)
    
    assert assessment.has_credible_contradicting_evidence is True
    assert assessment.has_direct_support is False
    assert state in [EvidenceState.UNSUPPORTED, EvidenceState.CONFLICTING]

