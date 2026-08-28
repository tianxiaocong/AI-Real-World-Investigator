import logging
import numpy as np
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field

from app.models.schemas import ClaimType, ConfidenceLevel
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
    Verifiability,
    InputType
)
from app.engine.verdict_rules import (
    assess_evidence_for_claim,
    compute_evidence_state,
    resolve_provenance_target
)
from app.providers.llm.base import LLMProvider
from app.providers.llm import get_llm_provider

logger = logging.getLogger(__name__)

def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    if not vec_a or not vec_b:
        return 0.0
    a = np.array(vec_a, dtype=float)
    b = np.array(vec_b, dtype=float)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

def _map_source_type_to_tier(st_val: Any, domain: str = "") -> SourceTier:
    st_upper = str(st_val.value if hasattr(st_val, "value") else st_val).upper()
    if st_upper in ("OFFICIAL", "GOVERNMENT"):
        return SourceTier.OFFICIAL
    if st_upper in ("NEWS", "DATABASE", "ACADEMIC"):
        return SourceTier.AUTHORITATIVE
    if st_upper in ("INDUSTRY", "VENDOR"):
        return SourceTier.INDUSTRY
    if st_upper in ("FORUM", "COMMUNITY", "BLOG"):
        return SourceTier.COMMUNITY
    
    d = (domain or "").lower()
    if any(g in d for g in [".gov", "sec.gov", "samr.gov", ".edu", "court.gov"]):
        return SourceTier.OFFICIAL
    if any(o in d for o in ["reuters.com", "bloomberg.com", "apnews.com", "wsj.com", "ft.com", "xinhuanet.com", "cctv.com"]):
        return SourceTier.AUTHORITATIVE
    if any(m in d for m in ["36kr.com", "ithome.com", "thepaper.cn", "caixin.com", "sina.com.cn", "163.com", "qq.com"]):
        return SourceTier.MAINSTREAM
    if any(i in d for i in ["techcrunch.com", "huxiu.com", "geekpark.net", "infoq.cn"]):
        return SourceTier.INDUSTRY
    if any(c in d for c in ["zhihu.com", "weibo.com", "reddit.com", "x.com"]):
        return SourceTier.COMMUNITY
    return SourceTier.UNKNOWN

class ConflictJudgement(BaseModel):
    is_conflicting: bool = Field(..., description="True if statement A and statement B present irreconcilable, contradictory facts or opposing figures.")
    is_supporting: bool = Field(..., description="True if statement A and B describe and corroborate the same underlying proposition or fact.")
    explanation: str = Field(..., description="Brief explanation of why they agree or conflict.")

VERIFIER_SYSTEM_PROMPT = """You are an impartial Supreme Fact-Checking Arbiter and Intelligence Verification Arbiter.
Given two statements regarding the same subject, decide if they:
1. SUPPORT each other (corroborating the same fact, milestone, or mutually reinforcing details)
2. CONFLICT with each other (contradictory figures, opposing dates, disputed outcomes, or mutual denial)
3. NEUTRAL / DIFFERENT ASPECTS (unrelated details or distinct topics)
"""

class VerificationAgent:
    """
    Unified Verification Agent (Phase 5C Architecture Convergence).
    Performs canonical claim clustering via embeddings and semantic pairwise LLM arbitration,
    then strictly delegates all independent source calculation, origin graph resolution,
    and 6-state verdict determination to the deterministic verdict_rules.py engine.
    """
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm = llm_provider or get_llm_provider(tier="reasoning")

    async def verify_and_cluster_claims(self, claims_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not claims_data:
            return []

        # Step 1: Initialize working claim items
        working_claims: List[Dict[str, Any]] = []
        for c in claims_data:
            c_copy = dict(c)
            if "sources" not in c_copy or not c_copy["sources"]:
                c_copy["sources"] = [{
                    "id": c_copy.get("source_id", ""),
                    "url": c_copy.get("source_url", ""),
                    "domain": c_copy.get("source_domain", ""),
                    "title": c_copy.get("source_title", ""),
                    "source_type": c_copy.get("source_type", "OTHER"),
                    "credibility_score": c_copy.get("credibility_score", 0.5),
                    "exact_quote": c_copy.get("exact_quote", ""),
                    "char_start": c_copy.get("char_start"),
                    "char_end": c_copy.get("char_end"),
                    "context_prefix": c_copy.get("context_prefix", ""),
                    "context_suffix": c_copy.get("context_suffix", ""),
                    "origin_source_id": c_copy.get("origin_source_id"),
                    "origin_domain": c_copy.get("origin_domain")
                }]
            c_copy["contradictions"] = []
            c_copy["contradicting_claims"] = []
            working_claims.append(c_copy)

        # Step 2: Semantic clustering & merging (Canonical Claim Aggregation)
        merged_clusters: List[Dict[str, Any]] = []
        merged_indices: Set[int] = set()

        n = len(working_claims)
        for i in range(n):
            if i in merged_indices:
                continue

            canonical = working_claims[i]
            merged_indices.add(i)

            for j in range(i + 1, n):
                if j in merged_indices:
                    continue

                candidate = working_claims[j]
                emb1 = canonical.get("embedding")
                emb2 = candidate.get("embedding")

                sim = 0.0
                if emb1 and emb2:
                    sim = cosine_similarity(emb1, emb2)

                if sim > 0.65:
                    judgement = await self._judge_pair(canonical["statement"], candidate["statement"])
                    
                    if judgement.is_supporting:
                        logger.info(f"Corroborating claims merged: '{canonical['statement'][:30]}' <== '{candidate['statement'][:30]}'")
                        merged_indices.add(j)
                        
                        existing_urls = {s.get("url") for s in canonical["sources"]}
                        for src in candidate.get("sources", []):
                            if src.get("url") not in existing_urls or not src.get("url"):
                                canonical["sources"].append(src)
                                if src.get("url"):
                                    existing_urls.add(src.get("url"))

                        if candidate.get("confidence") == ConfidenceLevel.HIGH:
                            canonical["confidence"] = ConfidenceLevel.HIGH

                    elif judgement.is_conflicting:
                        logger.info(f"Conflict identified between: '{canonical['statement'][:30]}' vs '{candidate['statement'][:30]}'")
                        conflict_info_1 = {
                            "opposing_statement": candidate["statement"],
                            "opposing_domain": candidate.get("sources", [{}])[0].get("domain", "外部信源"),
                            "reason": judgement.explanation
                        }
                        conflict_info_2 = {
                            "opposing_statement": canonical["statement"],
                            "opposing_domain": canonical.get("sources", [{}])[0].get("domain", "外部信源"),
                            "reason": judgement.explanation
                        }
                        canonical["contradictions"].append(conflict_info_1)
                        canonical["contradicting_claims"].append(conflict_info_1)
                        candidate["contradictions"].append(conflict_info_2)
                        candidate["contradicting_claims"].append(conflict_info_2)

            merged_clusters.append(canonical)

        # Step 3: Final verdict calculation strictly via unified verdict_rules.py engine
        final_claims: List[Dict[str, Any]] = []
        for claim in merged_clusters:
            raw_sources = claim.get("sources", [])
            
            source_objects: List[Source] = []
            provenance_objects: List[SourceProvenance] = []
            evidence_objects: List[Evidence] = []
            
            for idx, s in enumerate(raw_sources):
                s_id = s.get("id") or f"s-{idx+1:02d}"
                s_tier = _map_source_type_to_tier(s.get("source_type", "OTHER"), s.get("domain", ""))
                src = Source(
                    id=s_id,
                    url=s.get("url") or "",
                    domain=s.get("domain") or "",
                    title=s.get("title") or "",
                    source_tier=s_tier
                )
                source_objects.append(src)
                
                # Check for origin provenance
                if s.get("origin_source_id"):
                    provenance_objects.append(
                        SourceProvenance(
                            source_id=s_id,
                            origin_source_id=s["origin_source_id"],
                            provenance_type=ProvenanceType.CITES if s.get("provenance_type") == "CITES" else ProvenanceType.REPUBLISHES
                        )
                    )
                elif s.get("origin_domain"):
                    res_id = resolve_provenance_target(s["origin_domain"], source_objects)
                    if res_id and res_id != s_id:
                        provenance_objects.append(
                            SourceProvenance(
                                source_id=s_id,
                                origin_source_id=res_id,
                                provenance_type=ProvenanceType.REPUBLISHES
                            )
                        )
                
                # Construct Evidence
                exact_quote = (s.get("exact_quote") or "").strip()
                if exact_quote:
                    # Valid exact quote extracted from source
                    evidence_objects.append(
                        Evidence(
                            id=f"e-{claim.get('id', 'c')}-{idx}",
                            source_id=s_id,
                            claim_id=claim.get("id", "c"),
                            exact_quote=exact_quote,
                            supports_claim=True,
                            contradicts_claim=False,
                            directness=EvidenceDirectness.DIRECT,
                            scope_match=True
                        )
                    )
                else:
                    # No quote extracted -> Strictly non-supporting background context
                    evidence_objects.append(
                        Evidence(
                            id=f"e-{claim.get('id', 'c')}-{idx}",
                            source_id=s_id,
                            claim_id=claim.get("id", "c"),
                            exact_quote="",
                            supports_claim=False,
                            contradicts_claim=False,
                            directness=EvidenceDirectness.CONTEXTUAL,
                            scope_match=False,
                            evidence_note="No exact verbatim quote anchored; treated strictly as non-supporting background context."
                        )
                    )

            # Contradicting Evidence
            for c_idx, ct in enumerate(claim.get("contradictions", [])):
                opp_id = f"s-opp-{c_idx+1}"
                opp_src = Source(
                    id=opp_id,
                    domain=ct.get("opposing_domain", "外部信源"),
                    title=ct.get("opposing_statement", ""),
                    source_tier=SourceTier.AUTHORITATIVE
                )
                source_objects.append(opp_src)
                evidence_objects.append(
                    Evidence(
                        id=f"e-opp-{c_idx}",
                        source_id=opp_id,
                        claim_id=claim.get("id", "c"),
                        exact_quote=ct.get("opposing_statement", ""),
                        supports_claim=False,
                        contradicts_claim=True,
                        directness=EvidenceDirectness.DIRECT,
                        scope_match=True,
                        evidence_note=ct.get("reason", "")
                    )
                )

            # Determine verifiability
            c_type = claim.get("claim_type", ClaimType.FACT_STATEMENT)
            c_type_val = c_type.value if hasattr(c_type, "value") else str(c_type)
            verifiability = Verifiability.PUBLICLY_VERIFIABLE
            if c_type_val in ("OPINION", "INFERENCE"):
                verifiability = Verifiability.NOT_PUBLICLY_VERIFIABLE

            claim_obj = Claim(
                id=claim.get("id", "c-01"),
                original_input=claim.get("statement", ""),
                input_type=InputType.TEXT,
                statement=claim.get("statement", ""),
                claim_index=0,
                verifiability=verifiability,
                verifiability_reason="公开资料检索核验" if verifiability == Verifiability.PUBLICLY_VERIFIABLE else "主观观点/非公开推论",
                verified_as_of="2026-08-28"
            )

            assessment: EvidenceAssessment = assess_evidence_for_claim(
                claim=claim_obj,
                sources=source_objects,
                evidences=evidence_objects,
                provenances=provenance_objects
            )
            evidence_state: EvidenceState = compute_evidence_state(assessment, claim_obj.verifiability)

            # Assign strictly unified 6-state outputs
            claim["evidence_state"] = evidence_state.value
            claim["verification_status"] = evidence_state.value
            claim["independent_sources_count"] = assessment.independent_source_count
            claim["origin_source_count"] = assessment.origin_source_count
            claim["republish_count"] = assessment.republish_count
            claim["supporting_evidence_count"] = assessment.supporting_evidence_count
            claim["contradicting_evidence_count"] = assessment.contradicting_evidence_count
            claim["has_direct_support"] = assessment.has_direct_support
            claim["has_strong_independent_support"] = assessment.has_strong_independent_support
            claim["has_credible_contradicting_evidence"] = assessment.has_credible_contradicting_evidence

            # Build human readable verdict reasons
            verdict_reasons = []
            if evidence_state == EvidenceState.SUFFICIENT:
                claim["verdict_summary"] = f"🟢 证据充分 ({assessment.independent_source_count} 个独立来源直接证实)"
                verdict_reasons.append(f"✓ 获得 {assessment.independent_source_count} 个独立信息源交叉证实")
                verdict_reasons.append("✓ 获得权威/官方直接支持，且当前检索范围内未发现直接冲突")
            elif evidence_state == EvidenceState.STRONG:
                claim["verdict_summary"] = f"🟢 证据较强 ({assessment.independent_source_count} 个独立来源)"
                verdict_reasons.append(f"✓ 获得 {assessment.independent_source_count} 个独立来源支持，无有效反驳证据")
            elif evidence_state == EvidenceState.CONFLICTING:
                claim["verdict_summary"] = f"🔴 存在争议 ({len(claim['contradictions'])} 处口径冲突)"
                for ct in claim["contradictions"]:
                    verdict_reasons.append(f"⚠️ 与信源 [{ct.get('opposing_domain')}] 存在冲突：{ct.get('reason')}")
            elif evidence_state == EvidenceState.UNSUPPORTED:
                claim["verdict_summary"] = "🔴 证据不支持 (发现直接反驳证据)"
                verdict_reasons.append("发现可靠的反驳证据证实该主张不成立。")
            elif evidence_state == EvidenceState.NOT_ASSESSABLE:
                claim["verdict_summary"] = "⚪ 无法评估 (非公开可验证事实/观点推论)"
                verdict_reasons.append("该事项缺乏公开可验证渠道或属于主观推论。")
            else:
                # INSUFFICIENT
                if assessment.independent_source_count == 1:
                    first_dom = source_objects[0].domain if source_objects else "单一信源"
                    claim["verdict_summary"] = f"🟠 单一来源 ({first_dom})"
                    verdict_reasons.append(f"ℹ️ 目前仅由单一信源 [{first_dom}] 提及")
                    verdict_reasons.append("ℹ️ 尚未获得第二方独立信源交叉印证，证据不足")
                else:
                    claim["verdict_summary"] = "⚪ 证据不足"
                    verdict_reasons.append("缺乏确凿一手出处或独立交叉验证，建议审慎采信。")

            claim["verdict_reasons"] = verdict_reasons
            claim["reasoning"] = "\n".join(verdict_reasons)
            final_claims.append(claim)

        return final_claims

    async def _judge_pair(self, stmt_a: str, stmt_b: str) -> ConflictJudgement:
        prompt = (
            f"Statement A: \"{stmt_a}\"\n"
            f"Statement B: \"{stmt_b}\"\n\n"
            f"Do these two statements support each other (same fact or mutually corroborating), conflict with each other (contradictory metrics, opposing claims), or describe unrelated aspects?"
        )
        try:
            return await self.llm.generate_structured(
                prompt=prompt,
                response_model=ConflictJudgement,
                system_prompt=VERIFIER_SYSTEM_PROMPT,
                temperature=0.0
            )
        except Exception as e:
            logger.warning(f"Pair verification error: {e}")
            return ConflictJudgement(is_conflicting=False, is_supporting=False, explanation="Analysis skipped.")
