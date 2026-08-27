"""
AI Claim Verifier — Verdict Rule Engine (v4 Final)

严格遵循规则引擎计算判定，LLM 只负责后续解释。
不使用浮点置信度，不进行不可靠的 Tier 大小简单比拼。
"""

from __future__ import annotations
from typing import List, Dict, Set, Optional

from app.models.verification_models import (
    Claim,
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
    OverallCoverage,
    Verifiability,
    InputType
)


def assess_evidence_for_claim(
    claim: Claim,
    sources: List[Source],
    evidences: List[Evidence],
    provenances: Optional[List[SourceProvenance]] = None
) -> EvidenceAssessment:
    """
    将原始提取的证据列表和来源，压缩计算为结构化的 EvidenceAssessment 中间态。
    - 计算真正去重的独立信息源数量 (origin-based provenance)
    - 评估支持侧和反驳侧的直接性与有效性
    """
    source_map: Dict[str, Source] = {s.id: s for s in sources}
    provenance_map: Dict[str, SourceProvenance] = {
        p.source_id: p for p in (provenances or [])
    }

    # 1. 独立信息源去重计算 (Origin-based de-duplication)
    origin_sources: Set[str] = set()
    republish_count = 0
    original_count = 0

    for s in sources:
        prov = provenance_map.get(s.id)
        if prov:
            if prov.provenance_type == ProvenanceType.ORIGINAL or not prov.origin_source_id:
                origin_sources.add(s.id)
                original_count += 1
            elif prov.provenance_type in (ProvenanceType.REPUBLISHES, ProvenanceType.CITES):
                origin_sources.add(prov.origin_source_id)
                republish_count += 1
            else:
                origin_sources.add(s.id)
        else:
            # 默认自身作为一个源
            origin_sources.add(s.domain if s.domain else s.id)
            original_count += 1

    independent_count = len(origin_sources)

    # 2. 统计证据角色与直接性
    supporting_count = 0
    contradicting_count = 0
    context_count = 0

    has_direct_support = False
    has_supporting_official = False
    has_credible_contradiction = False

    # 统计具备直接支撑的高质量独立源集合
    direct_supporting_origins: Set[str] = set()

    for ev in evidences:
        src = source_map.get(ev.source_id)
        src_tier = src.source_tier if src else SourceTier.UNKNOWN

        # 检查是否为同源归属
        prov = provenance_map.get(ev.source_id)
        origin_key = (prov.origin_source_id if (prov and prov.origin_source_id) 
                      else (src.domain if src else ev.source_id))

        if ev.supports_claim is True and ev.scope_match:
            supporting_count += 1
            if ev.directness == EvidenceDirectness.DIRECT:
                has_direct_support = True
                direct_supporting_origins.add(origin_key)
                if src_tier == SourceTier.OFFICIAL:
                    has_supporting_official = True
        elif ev.contradicts_claim is True and ev.scope_match:
            contradicting_count += 1
            # 具备可信反驳证据要求：DIRECT 且来自非纯社区低质匿名源
            if ev.directness in (EvidenceDirectness.DIRECT, EvidenceDirectness.INDIRECT):
                if src_tier in (SourceTier.OFFICIAL, SourceTier.AUTHORITATIVE, SourceTier.MAINSTREAM, SourceTier.INDUSTRY):
                    has_credible_contradiction = True
                elif src_tier == SourceTier.COMMUNITY and ev.directness == EvidenceDirectness.DIRECT:
                    # 社区源如果有详实反证材料也可以记录
                    has_credible_contradiction = True
        else:
            context_count += 1

    # 强独立支持：至少 2 个独立来源，且至少存在直接支撑
    has_strong_independent_support = (
        independent_count >= 2 and 
        len(direct_supporting_origins) >= 2
    )

    return EvidenceAssessment(
        claim_id=claim.id,
        total_sources_found=len(sources),
        independent_source_count=independent_count,
        origin_source_count=original_count,
        republish_count=republish_count,
        supporting_evidence_count=supporting_count,
        contradicting_evidence_count=contradicting_count,
        context_only_count=context_count,
        has_direct_support=has_direct_support,
        has_strong_independent_support=has_strong_independent_support,
        has_supporting_official_source=has_supporting_official,
        has_credible_contradicting_evidence=has_credible_contradiction,
        time_consistent=True,
        value_consistent=True
    )


def compute_evidence_state(
    assessment: EvidenceAssessment,
    verifiability: Verifiability
) -> EvidenceState:
    """
    根据证据结构化评估结果与公开可验证性，由规则引擎严格计算单 Claim 的 EvidenceState。
    """
    # 1. 无法评估：没有找到任何相关证据 + 本身难以通过公开资料验证
    if (assessment.total_sources_found == 0 
        and verifiability in (Verifiability.HARD_TO_VERIFY, Verifiability.NOT_PUBLICLY_VERIFIABLE)):
        return EvidenceState.NOT_ASSESSABLE

    # 2. 证据不支持 (有可靠证据反驳)：必须有可靠反驳，且缺乏可信直接支持
    if assessment.has_credible_contradicting_evidence and not assessment.has_direct_support:
        return EvidenceState.UNSUPPORTED

    # 3. 证据冲突：既有可靠反驳，又有可靠直接支持
    if assessment.has_credible_contradicting_evidence and assessment.has_direct_support:
        return EvidenceState.CONFLICTING

    # 4. 证据充分：≥2 独立来源直接支持 + 官方一手来源直接证实 + 无可信反驳
    if (assessment.independent_source_count >= 2
        and assessment.has_supporting_official_source
        and assessment.has_direct_support
        and not assessment.has_credible_contradicting_evidence
        and assessment.value_consistent is not False):
        return EvidenceState.SUFFICIENT

    # 5. 证据较强：≥2 独立来源直接支持 + 无可信反驳 (哪怕没有官方一手源)
    if (assessment.has_strong_independent_support
        and not assessment.has_credible_contradicting_evidence
        and assessment.value_consistent is not False):
        return EvidenceState.STRONG

    # 6. 证据不足：其余情况 (例如：0个证据但可公开验证、单一来源、只有转载、只有间接/背景提及等)
    return EvidenceState.INSUFFICIENT


def compute_overall_state(verdicts: List[Verdict]) -> OverallState:
    """
    多 Claim 完整性覆盖计算（Coverage），杜绝粗暴的 '取最弱'。
    """
    if not verdicts:
        return OverallState.NOT_ASSESSABLE

    states = [v.evidence_state for v in verdicts]
    assessable = [s for s in states if s != EvidenceState.NOT_ASSESSABLE]

    if not assessable:
        return OverallState.NOT_ASSESSABLE

    positive_set = {EvidenceState.SUFFICIENT, EvidenceState.STRONG}
    negative_set = {EvidenceState.UNSUPPORTED}

    all_positive = all(s in positive_set for s in assessable)
    all_negative = all(s in negative_set for s in assessable)
    has_positive = any(s in positive_set for s in assessable)
    has_negative = any(s in negative_set for s in assessable)
    has_conflict = EvidenceState.CONFLICTING in assessable

    if all_positive:
        return OverallState.FULLY_SUPPORTED
    if all_negative:
        return OverallState.FULLY_UNSUPPORTED
    if has_conflict or (has_positive and has_negative):
        return OverallState.MIXED
    if has_positive:
        return OverallState.PARTIALLY_SUPPORTED

    return OverallState.NOT_ASSESSABLE


def generate_overall_coverage(
    original_input: str,
    input_type: InputType,
    claims: List[Claim],
    verdicts: List[Verdict]
) -> OverallCoverage:
    """
    汇总生成多 Claim 整体核验覆盖报告。
    """
    overall_state = compute_overall_state(verdicts)

    suff = sum(1 for v in verdicts if v.evidence_state == EvidenceState.SUFFICIENT)
    strong = sum(1 for v in verdicts if v.evidence_state == EvidenceState.STRONG)
    insuff = sum(1 for v in verdicts if v.evidence_state == EvidenceState.INSUFFICIENT)
    conf = sum(1 for v in verdicts if v.evidence_state == EvidenceState.CONFLICTING)
    unsupp = sum(1 for v in verdicts if v.evidence_state == EvidenceState.UNSUPPORTED)
    not_ass = sum(1 for v in verdicts if v.evidence_state == EvidenceState.NOT_ASSESSABLE)

    total = len(claims)
    parts = []
    if suff + strong > 0:
        parts.append(f"{suff + strong} 个证据充分/较强")
    if conf > 0:
        parts.append(f"{conf} 个存在争议冲突")
    if insuff > 0:
        parts.append(f"{insuff} 个证据不足")
    if unsupp > 0:
        parts.append(f"{unsupp} 个有证据反驳")
    if not_ass > 0:
        parts.append(f"{not_ass} 个公开资料无法核验")

    detail_str = "，".join(parts) if parts else "尚未获得有效判定"
    summary = f"你提供的说法包含 {total} 个可验证事实点：其中 {detail_str}。"

    return OverallCoverage(
        original_input=original_input,
        input_type=input_type,
        claims=claims,
        verdicts=verdicts,
        overall_state=overall_state,
        sufficient_count=suff,
        strong_count=strong,
        insufficient_count=insuff,
        conflicting_count=conf,
        unsupported_count=unsupp,
        not_assessable_count=not_ass,
        coverage_summary=summary
    )
