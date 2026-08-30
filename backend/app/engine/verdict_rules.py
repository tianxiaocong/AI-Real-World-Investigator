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

def resolve_provenance_target(target_ref: Optional[str], sources: List[Source]) -> Optional[str]:
    """
    Canonical resolver: maps referenced_url or explicit source identifier to a source_id in the current manifest.
    Strict Identity Principle:
    1. Exact source_id match (case-insensitive) -> Returns source.id
    2. Exact canonical URL match (normalized protocol, www, trailing slashes) -> Returns source.id
    3. Domain-only, title fuzzy, or author fuzzy matches are STRICTLY DISALLOWED to prevent accidental merges of different articles.
    Returns None if no unambiguous identity match is found (Strict Isolation).
    """
    if not target_ref:
        return None
    target_clean = target_ref.strip().lower()
    
    # 1. Exact direct match with source_id (e.g. "s-01", "s-02", "src-1")
    for src in sources:
        if src.id.lower() == target_clean:
            return src.id
            
    def _normalize_url(u: str) -> str:
        u_clean = u.strip().lower()
        if u_clean.startswith("http://"):
            u_clean = u_clean[7:]
        elif u_clean.startswith("https://"):
            u_clean = u_clean[8:]
        elif u_clean.startswith("mock://"):
            u_clean = u_clean[7:]
        if u_clean.startswith("www."):
            u_clean = u_clean[4:]
        return u_clean.rstrip("/")

    target_norm_url = _normalize_url(target_clean)
    
    # 2. Exact Canonical URL match (requires path/article specificity; pure root domain is rejected)
    if "/" in target_norm_url:
        for src in sources:
            if src.url and _normalize_url(src.url) == target_norm_url:
                return src.id

    return None


def _resolve_ultimate_origin(source_id: str, provenance_map: Dict[str, SourceProvenance], source_map: Dict[str, Source]) -> str:
    """
    Traverse the provenance graph to find the root origin of a source.
    Resolves multi-level republication chains (S3 -> S2 -> S1) to a single cluster.
    """
    visited = set()
    curr = source_id
    
    while curr in provenance_map:
        if curr in visited:
            import logging
            logging.warning(f"CyclicProvenanceWarning: Cyclic provenance detected involving '{curr}'. Isolating origin to '{source_id}'.")
            return source_id
            
        visited.add(curr)
        prov = provenance_map[curr]
        if prov.provenance_type in (ProvenanceType.REPUBLISHES, ProvenanceType.CITES) and prov.origin_source_id:
            curr = prov.origin_source_id
        else:
            break
            
    return curr

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
        origin_key = _resolve_ultimate_origin(s.id, provenance_map, source_map)
        origin_sources.add(origin_key)
        
        if prov and prov.provenance_type in (ProvenanceType.REPUBLISHES, ProvenanceType.CITES):
            republish_count += 1
        else:
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
        origin_key = _resolve_ultimate_origin(ev.source_id, provenance_map, source_map)
        # --- DETERMINISTIC RULE 1: Evidence Role Admissibility Filter ---
        evidence_role_val = getattr(ev, "evidence_role", None)
        ev_role_str = evidence_role_val.name if hasattr(evidence_role_val, "name") else str(evidence_role_val)
        
        element_role = getattr(ev, "element_role", "MAIN")
        
        is_non_evidentiary = False
        if ev_role_str in ("NAVIGATION_OR_LINK", "BOILERPLATE", "SPECULATION_OR_QUESTION"):
            is_non_evidentiary = True
        elif element_role in ("ASIDE", "NAV", "FOOTER") and ev_role_str != "FACTUAL_ASSERTION":
            is_non_evidentiary = True
            
        if is_non_evidentiary:
            ev.is_admissible_factual_evidence = False
            ev.supports_claim = False
            ev.contradicts_claim = False
            ev.directness = EvidenceDirectness.CONTEXTUAL
            note = f"Non-evidentiary excluded (Role: {ev_role_str}, DOM: {element_role})"
            ev.evidence_note = f"{ev.evidence_note} | {note}" if ev.evidence_note else note

        # --- DETERMINISTIC RULE 2: Scope Integrity Filter ---
        if getattr(ev, "is_admissible_factual_evidence", True) is True:
            scope_issues = getattr(ev, "scope_issues", [])
            high_severity_issues = [issue for issue in scope_issues if (hasattr(issue.severity, 'name') and issue.severity.name == "HIGH") or issue.severity == "HIGH"]
            low_severity_issues = [issue for issue in scope_issues if (hasattr(issue.severity, 'name') and issue.severity.name == "LOW") or issue.severity == "LOW"]
            
            if high_severity_issues:
                ev.supports_claim = False
                ev.directness = EvidenceDirectness.CONTEXTUAL
                issue_descs = [f"[{i.issue_type.name if hasattr(i.issue_type, 'name') else str(i.issue_type)}]" for i in high_severity_issues]
                note = f"HIGH severity scope overclaim: {', '.join(issue_descs)}"
                ev.evidence_note = f"{ev.evidence_note} | {note}" if ev.evidence_note else note
            elif low_severity_issues:
                issue_descs = [f"[{i.issue_type.name if hasattr(i.issue_type, 'name') else str(i.issue_type)}]" for i in low_severity_issues]
                note = f"LOW severity benign variation: {', '.join(issue_descs)}"
                ev.evidence_note = f"{ev.evidence_note} | {note}" if ev.evidence_note else note

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
                if src_tier in (SourceTier.OFFICIAL, SourceTier.AUTHORITATIVE, SourceTier.MAINSTREAM, SourceTier.INDUSTRY, SourceTier.UNKNOWN):
                    has_credible_contradiction = True
                elif src_tier == SourceTier.COMMUNITY and ev.directness == EvidenceDirectness.DIRECT:
                    # 社区源如果有详实反证材料也可以记录
                    has_credible_contradiction = True
        else:
            context_count += 1

    # 强独立直接支持：至少 2 个独立 origin 提供直接支持 (DIRECT + scope_match)
    direct_origin_count = len(direct_supporting_origins)
    has_strong_independent_support = (direct_origin_count >= 2)

    # --- DETERMINISTIC RULE 3: Consistency Calculation from Scope Issues ---
    has_high_quantifier_conflict = False
    has_high_temporal_conflict = False

    for ev in evidences:
        scope_issues = getattr(ev, "scope_issues", [])
        for issue in scope_issues:
            itype = issue.issue_type.name if hasattr(issue.issue_type, 'name') else str(issue.issue_type)
            isev = issue.severity.name if hasattr(issue.severity, 'name') else str(issue.severity)
            if isev == "HIGH":
                if itype in ("QUANTIFIER", "POPULATION", "CONDITION", "EXCEPTION"):
                    has_high_quantifier_conflict = True
                elif itype in ("TEMPORAL", "ENTITY_VERSION"):
                    has_high_temporal_conflict = True

    value_consistent = not has_high_quantifier_conflict
    time_consistent = not has_high_temporal_conflict

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
        direct_supporting_origin_count=direct_origin_count,
        has_strong_independent_support=has_strong_independent_support,
        has_supporting_official_source=has_supporting_official,
        has_credible_contradicting_evidence=has_credible_contradiction,
        time_consistent=time_consistent,
        value_consistent=value_consistent
    )


def compute_evidence_state(
    assessment: EvidenceAssessment,
    verifiability: Verifiability
) -> EvidenceState:
    """
    根据证据结构化评估结果与公开可验证性，由规则引擎严格计算单 Claim 的 EvidenceState。
    """
    # 1. 无法评估：非公开可验证事实（主观观点推论），或没有找到任何证据且极难公开验证
    if verifiability == Verifiability.NOT_PUBLICLY_VERIFIABLE:
        return EvidenceState.NOT_ASSESSABLE
    if (assessment.total_sources_found == 0 
        and verifiability == Verifiability.HARD_TO_VERIFY):
        return EvidenceState.NOT_ASSESSABLE

    # 2. 证据不支持 (有可靠证据反驳)：必须有可靠反驳，且缺乏可信直接支持
    if assessment.has_credible_contradicting_evidence and not assessment.has_direct_support:
        return EvidenceState.UNSUPPORTED

    # 3. 证据冲突：既有可靠反驳，又有可靠直接支持
    if assessment.has_credible_contradicting_evidence and assessment.has_direct_support:
        return EvidenceState.CONFLICTING

    # 4. 证据充分：≥2 独立 origin 直接支持 + 官方一手来源直接证实 + 无可信反驳 + 数值/时空一致
    # 严格安全不变量：必须满足 has_strong_independent_support (direct_supporting_origin_count >= 2)，
    # 彻底杜绝使用全量无关 sources 数量充数的假充分现象！
    if (assessment.has_strong_independent_support
        and assessment.has_supporting_official_source
        and not assessment.has_credible_contradicting_evidence
        and assessment.value_consistent is not False
        and assessment.time_consistent is not False):
        return EvidenceState.SUFFICIENT

    # 5. 证据较强：≥2 独立 origin 直接支持 + 无可信反驳 + 数值/时空一致 (哪怕没有官方一手源)
    if (assessment.has_strong_independent_support
        and not assessment.has_credible_contradicting_evidence
        and assessment.value_consistent is not False
        and assessment.time_consistent is not False):
        return EvidenceState.STRONG

    # 6. 证据不足：其余情况 (例如：0个证据但可公开验证、单一来源、只有转载、时空/数值口径冲突降级、只有间接/背景提及等)
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
