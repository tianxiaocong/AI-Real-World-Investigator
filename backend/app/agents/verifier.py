import logging
import numpy as np
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field
from app.models.schemas import VerificationStatus, ClaimType, ConfidenceLevel
from app.providers.llm.base import LLMProvider
from app.providers.llm import get_llm_provider

logger = logging.getLogger(__name__)

def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    a = np.array(vec_a, dtype=float)
    b = np.array(vec_b, dtype=float)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

try:
    import tldextract
    _tld_extractor = tldextract.TLDExtract(cache_dir=None)
except ImportError:
    _tld_extractor = None

def extract_root_domain(domain_or_url: str) -> str:
    """
    Extract true normalized root domain name using Public Suffix List.
    Handles 'mobile.reuters.com' -> 'reuters.com', 'news.bbc.co.uk' -> 'bbc.co.uk', etc.
    """
    if not domain_or_url:
        return "unknown"
    
    clean_target = domain_or_url.strip()
    if clean_target.startswith("mock://"):
        clean_target = clean_target.replace("mock://", "http://")

    if _tld_extractor:
        try:
            ext = _tld_extractor(clean_target)
            if ext.domain and ext.suffix:
                return f"{ext.domain}.{ext.suffix}".lower()
            if ext.domain:
                return ext.domain.lower()
        except Exception:
            pass

    # Fallback to hostname normalization
    if "://" in clean_target:
        parsed = urlparse(clean_target)
        host = parsed.hostname or clean_target
    else:
        host = clean_target.split(":")[0].split("/")[0]
    
    host = host.lower().strip()
    parts = host.split(".")
    if len(parts) > 2:
        two_part_tlds = {"com.cn", "gov.cn", "org.cn", "net.cn", "co.uk", "gov.uk", "ac.uk", "com.hk", "org.uk"}
        last_two = ".".join(parts[-2:])
        if last_two in two_part_tlds and len(parts) >= 3:
            return ".".join(parts[-3:])
        return ".".join(parts[-2:])
    return host

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
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm = llm_provider or get_llm_provider(tier="reasoning")

    async def verify_and_cluster_claims(self, claims_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes raw claims with embeddings and source metadata,
        performs canonical claim clustering (merging corroborated claims across sources),
        cross-examines conflicting pairs, computes independent domain statistics,
        and assigns dual-dimension ClaimType and VerificationStatus with structured reasons.
        """
        if not claims_data:
            return []

        # Step 1: Initialize working claim items
        working_claims: List[Dict[str, Any]] = []
        for c in claims_data:
            c_copy = dict(c)
            # Ensure sources list is present
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

                # Check for high similarity or potential conflict
                if sim > 0.65:
                    judgement = await self._judge_pair(canonical["statement"], candidate["statement"])
                    
                    if judgement.is_supporting:
                        # Merge candidate's sources into canonical claim
                        logger.info(f"Corroborating claims merged: '{canonical['statement'][:30]}' <== '{candidate['statement'][:30]}'")
                        merged_indices.add(j)
                        
                        # Add distinct sources
                        existing_urls = {s.get("url") for s in canonical["sources"]}
                        for src in candidate.get("sources", []):
                            if src.get("url") not in existing_urls or not src.get("url"):
                                canonical["sources"].append(src)
                                if src.get("url"):
                                    existing_urls.add(src.get("url"))

                        # Inherit higher confidence
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

        # Step 3: Final verdict calculation for each canonical claim
        final_claims: List[Dict[str, Any]] = []
        for claim in merged_clusters:
            sources = claim.get("sources", [])
            
            # Calculate Independent Root Domains and Origin Provenance
            unique_origins: Set[str] = set()
            tier_counts: Dict[str, int] = {}
            for s in sources:
                dom = extract_root_domain(s.get("domain") or s.get("url") or "")
                # If origin_domain is indicated (e.g. syndicated report from Bloomberg), use origin
                origin_dom = extract_root_domain(s.get("origin_domain")) if s.get("origin_domain") else dom
                if origin_dom and origin_dom != "unknown":
                    unique_origins.add(origin_dom)
                st = s.get("source_type", "OTHER")
                st_str = st.value if hasattr(st, "value") else str(st)
                tier_counts[st_str] = tier_counts.get(st_str, 0) + 1

            independent_count = max(1, len(unique_origins))
            claim["independent_sources_count"] = independent_count
            claim["source_tiers_summary"] = tier_counts

            c_type = claim.get("claim_type", ClaimType.FACT_STATEMENT)
            c_type_val = c_type.value if hasattr(c_type, "value") else str(c_type)

            has_contradictions = len(claim.get("contradictions", [])) > 0
            has_official = tier_counts.get("OFFICIAL", 0) > 0 or tier_counts.get("GOVERNMENT", 0) > 0
            has_authoritative = has_official or tier_counts.get("NEWS", 0) > 0 or tier_counts.get("DATABASE", 0) > 0 or tier_counts.get("ACADEMIC", 0) > 0

            # Determine Verification Status & Human Reasoning Checklist
            verdict_reasons: List[str] = []

            if c_type_val in ("OPINION", ClaimType.OPINION.value, "INFERENCE", ClaimType.INFERENCE.value):
                claim["verification_status"] = VerificationStatus.OPINION_ONLY
                claim["verdict_summary"] = "⚪ 观点推论 (主观评估/分析推导)"
                verdict_reasons.append("该主张属于行业分析师/媒体观点或逻辑推导，不作为客观确凿事实采信。")
                if independent_count > 1:
                    verdict_reasons.append(f"共 {independent_count} 个独立信源表达了类似观点倾向。")

            elif has_contradictions or c_type_val in ("DISPUTED", ClaimType.DISPUTED.value):
                claim["verification_status"] = VerificationStatus.DISPUTED
                claim["claim_type"] = ClaimType.DISPUTED
                claim["verdict_summary"] = f"🔴 存在争议 ({len(claim['contradictions'])} 处口径冲突)"
                for ct in claim["contradictions"]:
                    verdict_reasons.append(f"⚠️ 与信源 [{ct.get('opposing_domain')}] 存在冲突：{ct.get('reason')}")

            elif independent_count >= 2 and has_authoritative:
                claim["verification_status"] = VerificationStatus.CONFIRMED
                claim["verdict_summary"] = f"🟢 已确认 ({independent_count} 个独立信源)"
                domains_str = "、".join(list(unique_origins)[:3])
                verdict_reasons.append(f"✓ 经 {independent_count} 个独立权威信源交叉证实 ({domains_str})")
                if has_official:
                    verdict_reasons.append("✓ 获得一手官方或合规监管主体披露直接支持")
                verdict_reasons.append("✓ 当前检索范围内未发现直接冲突反证，事实链条自洽")

            elif has_official or (has_authoritative and claim.get("confidence") == ConfidenceLevel.HIGH):
                claim["verification_status"] = VerificationStatus.PROBABLE
                claim["verdict_summary"] = f"🟢 基本确认 ({list(unique_origins)[0] if unique_origins else '权威信源'})"
                verdict_reasons.append(f"✓ 获得权威信源 ({list(unique_origins)[0] if unique_origins else '主流披露'}) 明确报道")
                verdict_reasons.append("✓ 描述具体翔实，当前检索范围内暂无对立反证")

            elif independent_count == 1:
                claim["verification_status"] = VerificationStatus.SINGLE_SOURCE
                first_dom = list(unique_origins)[0] if unique_origins else "单一信源"
                claim["verdict_summary"] = f"🟠 单一来源 ({first_dom})"
                verdict_reasons.append(f"ℹ️ 目前仅由单一信源 [{first_dom}] 提及")
                verdict_reasons.append("ℹ️ 尚未获得第二方独立信源交叉印证，建议审慎参考")

            else:
                claim["verification_status"] = VerificationStatus.UNVERIFIED
                claim["verdict_summary"] = "⚪ 无法确认 (证据不足)"
                verdict_reasons.append("缺乏确凿一手出处，当前检索范围内未发现直接有效佐证。")

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
