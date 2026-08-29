"""
Unified Production Verification Service
The single, canonical business logic layer for fact verification across:
- /api/v1/verify (Fast Claim Verifier)
- /api/v1/investigations (Investigation Orchestrator)
- Phase 5D Real-Factual E2E Benchmark Runner
"""

import logging
from typing import List, Dict, Any, Optional, Tuple

from app.models.schemas import ClaimType, ConfidenceLevel, SourceType
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
from app.agents.claim_extractor import ClaimExtractorAgent
from app.engine.verdict_rules import (
    assess_evidence_for_claim,
    compute_evidence_state,
    resolve_provenance_target
)
from app.providers.llm.base import LLMProvider
from app.providers.llm import get_llm_provider

logger = logging.getLogger(__name__)

def _map_source_type_to_tier(st: Any, domain: str) -> SourceTier:
    """Helper to map string/enum source type to SourceTier"""
    st_str = st.value if hasattr(st, "value") else str(st).upper()
    if "OFFICIAL" in st_str or "GOV" in domain or "EDU" in domain:
        return SourceTier.OFFICIAL
    if "NEWS" in st_str or "AUTHORITATIVE" in st_str:
        return SourceTier.AUTHORITATIVE
    if "INDUSTRY" in st_str:
        return SourceTier.INDUSTRY
    if "MAINSTREAM" in st_str:
        return SourceTier.MAINSTREAM
    if "FORUM" in st_str or "SOCIAL" in st_str or "BLOG" in st_str:
        return SourceTier.COMMUNITY
    return SourceTier.UNKNOWN


def resolve_textual_provenance(target_ref: Optional[str], sources: List[Source]) -> Optional[str]:
    """
    Heuristic resolver: attempts to safely map a natural language citation (like 'The Information') 
    to exactly ONE source in the current manifest based on domain.
    If multiple sources belong to the same publisher, it safely bails (returns None).
    """
    if not target_ref:
        return None
        
    # 1. Try strict resolution first
    strict_match = resolve_provenance_target(target_ref, sources)
    if strict_match:
        return strict_match
        
    # 2. Heuristic domain/publisher match
    target_clean = target_ref.strip().lower()
    
    # Strip basic prefixes/suffixes for domain checks
    clean_target = target_clean.replace("https://", "").replace("http://", "").replace("www.", "")
    if "/" in clean_target:
        clean_target = clean_target.split("/")[0]

    matched_sources = []
    
    # Publisher name heuristics
    publisher_aliases = {
        "the information": "theinformation.com",
        "new york times": "nytimes.com",
        "nyt": "nytimes.com",
        "wsj": "wsj.com",
        "wall street journal": "wsj.com",
        "bloomberg": "bloomberg.com",
        "reuters": "reuters.com",
        "cnbc": "cnbc.com",
        "verge": "theverge.com",
        "the verge": "theverge.com",
    }
    
    target_domain = publisher_aliases.get(target_clean, clean_target)
    
    for src in sources:
        src_domain = src.url.lower().replace("https://", "").replace("http://", "").replace("www.", "")
        if "/" in src_domain:
            src_domain = src_domain.split("/")[0]
            
        if target_domain and len(target_domain) > 3 and (target_domain in src_domain or src_domain in target_domain):
            matched_sources.append(src)
            
    # ONLY map if we unambiguously match EXACTLY ONE source
    if len(matched_sources) == 1:
        return matched_sources[0].id
        
    return None


class VerificationService:
    """
    Unified Verification Service:
    Extracts atomic claims & quotes -> resolves provenance -> runs deterministic verdict rules.
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm = llm_provider or get_llm_provider(tier="fast")
        self.extractor = ClaimExtractorAgent(self.llm)

    async def verify_claim_against_sources(
        self,
        claim_statement: str,
        sources_data: List[Dict[str, Any]],
        verifiability: Verifiability = Verifiability.PUBLICLY_VERIFIABLE,
        target_entity: Optional[str] = None,
        enable_provenance: bool = True,
        enable_polarity_arbitration: bool = True,
        enable_relevant_window: bool = True
    ) -> Dict[str, Any]:
        """
        Executes end-to-end claim extraction, evidence alignment, provenance linking,
        and deterministic rule-engine verdict computation.

        :param claim_statement: The target statement being fact-checked
        :param sources_data: List of dicts with keys (id/source_id, url, title, domain, clean_text/raw_text, source_type)
        :param verifiability: Verifiability enum (default: PUBLICLY_VERIFIABLE)
        :param target_entity: Target entity keyword for relevant window positioning
        :param enable_provenance: If False, disables textual provenance resolution (Ablation A)
        :param enable_polarity_arbitration: If False, disables secondary LLM semantic polarity arbitration (Ablation B)
        :param enable_relevant_window: If False, disables targeted window selection and uses prefix slice (Ablation C)
        :return: Dict containing evidence_state, assessment, extracted_evidences, provenance_edges, etc.
        """
        target = target_entity or claim_statement[:30]

        # 1. Build Source manifest
        manifest_sources: List[Source] = []
        for s in sources_data:
            s_id = s.get("id") or s.get("source_id") or f"src-{len(manifest_sources)+1}"
            domain = s.get("domain") or ""
            tier = _map_source_type_to_tier(s.get("source_type") or s.get("source_tier_hint") or "OTHER", domain)
            manifest_sources.append(
                Source(
                    id=s_id,
                    url=s.get("url") or s.get("source_url") or "",
                    domain=domain,
                    title=s.get("title") or "",
                    source_tier=tier
                )
            )

        # 2. Extract atomic evidence & provenance from each source via ClaimExtractorAgent
        collected_evidences: List[Evidence] = []
        collected_provenance: List[SourceProvenance] = []
        raw_extractions: List[Dict[str, Any]] = []

        for s, src_obj in zip(sources_data, manifest_sources):
            raw_text = s.get("clean_text") or s.get("raw_text") or ""
            if not raw_text:
                continue

            extracted_items = await self.extractor.extract_claims_from_source(
                clean_text=raw_text,
                source_url=src_obj.url,
                source_type=src_obj.source_tier.value,
                target_name=target,
                use_relevant_window=enable_relevant_window
            )

            for item in extracted_items:
                quote = item.get("exact_quote", "").strip()
                if not quote:
                    continue

                raw_extractions.append(item)

                # Determine polarity
                stmt = item.get("statement", "")
                scope_match = item.get("quote_match") in ("EXACT", "FUZZY")

                supports = False
                contradicts = False
                reason = item.get("reasoning", "")

                if enable_polarity_arbitration:
                    # Evaluate support/contradiction against target claim via LLM semantic arbitration
                    eval_prompt = (
                        f"Target Claim: {claim_statement}\n"
                        f"Extracted Assertion: {stmt}\n"
                        f"Exact Source Quote: {quote}\n\n"
                        f"Does this extracted quote SUPPORT or CONTRADICT the Target Claim?\n"
                        f"Output strictly JSON with 'supports' (bool), 'contradicts' (bool), 'reason' (str)."
                    )
                    try:
                        eval_res = await self.llm.generate_text(prompt=eval_prompt, temperature=0.0)
                        eval_lower = eval_res.lower()
                        if '"supports": true' in eval_lower or '"supports":true' in eval_lower:
                            supports = True
                        if '"contradicts": true' in eval_lower or '"contradicts":true' in eval_lower:
                            contradicts = True
                    except Exception as e:
                        logger.debug(f"Polarity evaluation fallback: {e}")
                        if stmt and stmt.lower() in claim_statement.lower():
                            supports = True
                else:
                    # Ablation B baseline: naive string containment
                    if stmt and (stmt.lower() in claim_statement.lower() or claim_statement.lower() in stmt.lower()):
                        supports = True

                ev_id = f"ev-{src_obj.id}-{len(collected_evidences)+1}"
                directness = EvidenceDirectness.DIRECT if item.get("quote_match") == "EXACT" else EvidenceDirectness.CONTEXTUAL

                collected_evidences.append(
                    Evidence(
                        id=ev_id,
                        source_id=src_obj.id,
                        claim_id="c-target",
                        exact_quote=quote,
                        supports_claim=supports,
                        contradicts_claim=contradicts,
                        directness=directness,
                        scope_match=scope_match,
                        evidence_note=reason
                    )
                )

                # Check for explicit provenance relations
                if enable_provenance:
                    prov_meta = item.get("provenance")
                    if prov_meta and prov_meta.get("relation") in ("REPUBLISHES", "CITES"):
                        target_ref = prov_meta.get("cited_reference") or prov_meta.get("target_source_id") # backward compat
                        matched_id = resolve_textual_provenance(target_ref, manifest_sources)
                        if matched_id and matched_id != src_obj.id:
                            prov_type = ProvenanceType.REPUBLISHES if prov_meta["relation"] == "REPUBLISHES" else ProvenanceType.CITES
                            collected_provenance.append(
                                SourceProvenance(
                                    source_id=src_obj.id,
                                    origin_source_id=matched_id,
                                    provenance_type=prov_type
                                )
                            )

        # 3. Construct target Claim entity
        target_claim = Claim(
            id="c-target",
            original_input=claim_statement,
            input_type=InputType.TEXT,
            statement=claim_statement,
            claim_index=0,
            verifiability=verifiability,
            verifiability_reason="公开事实核验",
            verified_as_of="2026-08-28"
        )

        # 4. Deterministic Verdict Rules Engine
        assessment: EvidenceAssessment = assess_evidence_for_claim(
            claim=target_claim,
            sources=manifest_sources,
            evidences=collected_evidences,
            provenances=collected_provenance
        )

        evidence_state: EvidenceState = compute_evidence_state(assessment, verifiability)

        # 5. Build human-readable verdict reasons
        reasons = []
        if evidence_state in (EvidenceState.SUFFICIENT, EvidenceState.STRONG):
            reasons.append(f"找到 {assessment.independent_source_count} 个相互独立的有效信源支持该说法")
            if assessment.has_supporting_official_source:
                reasons.append("获得官方/一手渠道直接证实")
        elif evidence_state == EvidenceState.INSUFFICIENT:
            if assessment.total_sources_found == 0:
                reasons.append("尚未在当前检索范围内找到直接支持或反驳该说法的有效公开证据")
            elif assessment.independent_source_count <= 1:
                reasons.append(f"检索到 {assessment.total_sources_found} 个页面，但追溯后仅包含 {assessment.independent_source_count} 个独立原始信源，证据链不完整")
        elif evidence_state == EvidenceState.CONFLICTING:
            reasons.append("公开信源之间存在直接矛盾或口径冲突")
        elif evidence_state == EvidenceState.UNSUPPORTED:
            reasons.append("存在权威/官方一手信源的明确反驳或否认证据")
        elif evidence_state == EvidenceState.NOT_ASSESSABLE:
            reasons.append("该说法涉及主观观点、非公开推论或无法通过公开网络资料进行事实核验")

        return {
            "claim_statement": claim_statement,
            "evidence_state": evidence_state.value,
            "assessment": assessment.model_dump(),
            "independent_sources_count": assessment.independent_source_count,
            "total_sources_found": assessment.total_sources_found,
            "supporting_evidence_count": assessment.supporting_evidence_count,
            "contradicting_evidence_count": assessment.contradicting_evidence_count,
            "verdict_reasons": reasons,
            "extracted_evidences": [e.model_dump() for e in collected_evidences],
            "provenances": [p.model_dump() for p in collected_provenance],
            "raw_extractions": raw_extractions
        }
