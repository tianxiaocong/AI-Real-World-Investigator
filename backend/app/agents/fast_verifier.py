"""
AI Claim Verifier — Fast Verification Pipeline Agent (v4 Final)

执行单次快速事实核验：
1. Claim Decomposition (输入解析与多主张拆解)
2. Directed Search & Evidence Extraction (定向搜索与证据抽取)
3. Provenance Analysis (信息溯源与去重)
4. Rule Engine Verdict (确定性规则引擎判断)
5. Structured Explanation (清单式理由与缺口生成)
"""

import json
import uuid
import datetime
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

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
    OverallCoverage,
    Verifiability,
    InputType
)
from app.engine.verdict_rules import (
    assess_evidence_for_claim,
    compute_evidence_state,
    generate_overall_coverage,
    resolve_provenance_target
)
from app.providers.llm.base import LLMProvider
from app.providers.search.base import SearchProvider
from app.providers.search import get_search_provider

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  Structured LLM Output Schemas
# ──────────────────────────────────────────────

class RawDecomposedClaim(BaseModel):
    statement: str = Field(description="拆解出的单条可独立核验的陈述句子")
    subject: Optional[str] = Field(default=None, description="主语实体，例如 'OpenAI'、'马斯克'")
    predicate: Optional[str] = Field(default=None, description="谓词动作/属性，例如 '融资'、'毕业于'")
    object_value: Optional[str] = Field(default=None, description="宾语/数值，例如 '10亿美元'、'哈佛大学'")
    time_context: Optional[str] = Field(default=None, description="时间限定，例如 '2025年'、'昨天'")
    polarity: bool = Field(default=True, description="极性: True=肯定句, False=否定句")
    verifiability: Verifiability = Field(default=Verifiability.PUBLICLY_VERIFIABLE, description="公开可验证性评级")
    verifiability_reason: str = Field(default="", description="为什么该声明具有此级别的公开可验证性")


class DecomposeOutput(BaseModel):
    claims: List[RawDecomposedClaim] = Field(description="拆解出的主张列表")


class RawExtractedEvidence(BaseModel):
    exact_quote: str = Field(description="原始网页中的精确原话或直接事实陈述")
    context: str = Field(default="", description="引文上下文")
    supports_claim: bool = Field(default=False, description="是否直接支持该主张")
    contradicts_claim: bool = Field(default=False, description="是否直接反驳/否定该主张")
    directness: EvidenceDirectness = Field(default=EvidenceDirectness.CONTEXTUAL, description="直接性: DIRECT/INDIRECT/CONTEXTUAL")
    scope_match: bool = Field(default=True, description="讨论的事实和口径范围是否完全匹配")
    evidence_note: str = Field(default="", description="关键备注，例如金额差异或限制条件")
    origin_credit: Optional[str] = Field(default=None, description="若该报道提及真实源头，注明其名字，如 'Bloomberg'、'公司官方声明'")


class EvidenceExtractionBatch(BaseModel):
    evidences: List[RawExtractedEvidence] = Field(description="提取的证据列表")


class VerdictExplanationOutput(BaseModel):
    why_reasons: List[str] = Field(description="清单式'为什么这样判断'，每条以 ✓ 或 ! 或 ℹ️ 开头")
    evidence_gaps: List[str] = Field(description="尚未找到的关键证据缺口")
    next_step_advice: str = Field(description="给用户的下一步核实建议")


# ──────────────────────────────────────────────
#  Fast Claim Verifier Agent
# ──────────────────────────────────────────────

class FastClaimVerifierAgent:
    def __init__(self, llm_provider: LLMProvider, search_provider: Optional[SearchProvider] = None):
        self.llm = llm_provider
        self.search = search_provider or get_search_provider("mock")

    async def verify_input(
        self,
        input_text: str,
        input_type: InputType = InputType.TEXT,
        search_provider_name: Optional[str] = None
    ) -> OverallCoverage:
        """
        核心对外入口：接收用户输入的一句话或一段话，返回完整的结构化核验结果。
        """
        today_str = datetime.date.today().isoformat()
        
        # 1. Claim Decomposition (主张拆解)
        claims = await self._decompose_input(input_text, input_type, today_str)
        if not claims:
            claims = [
                Claim(
                    id=str(uuid.uuid4()),
                    original_input=input_text,
                    input_type=input_type,
                    statement=input_text.strip(),
                    claim_index=0,
                    verifiability=Verifiability.PUBLICLY_VERIFIABLE,
                    verifiability_reason="系统直接针对原始输入进行核验",
                    verified_as_of=today_str
                )
            ]

        verdicts: List[Verdict] = []
        
        # 2. 对每个拆解后的 Claim 分别执行定向证据检索与规则判定
        for claim in claims:
            verdict = await self._verify_single_claim(claim, today_str)
            verdicts.append(verdict)

        # 3. 汇总生成多 Claim 整体覆盖状态
        coverage = generate_overall_coverage(
            original_input=input_text,
            input_type=input_type,
            claims=claims,
            verdicts=verdicts
        )
        return coverage

    async def _decompose_input(
        self,
        input_text: str,
        input_type: InputType,
        today_str: str
    ) -> List[Claim]:
        """将用户输入的一句话拆解为 1~N 个独立可验证事实"""
        prompt = f"""你是一个专业的事实核验系统的主张拆解器（Claim Decomposer）。
请分析用户输入的文本，将其拆解为 1 到 4 个独立、具体、可在互联网公开信息中独立检索验证的原子事实主张。
如果用户输入本身就是单一简单事实，只需返回 1 个主张。

输入文本: "{input_text}"

请提取出结构化主张列表，并评定其公开可验证性：
- PUBLICLY_VERIFIABLE: 上市公司财报、官方公告、公开产品发布、知名法律诉讼等应有公开记录的事项
- LIMITED_PUBLIC: 创投早期融资、初创团队变动等仅有少量报道的事项
- HARD_TO_VERIFY: 私人行程、非公开内部言论等极难公开求证的事项
- NOT_PUBLICLY_VERIFIABLE: 纯主观偏好或无法通过公开资料验证的事项"""

        try:
            res: DecomposeOutput = await self.llm.generate_structured(
                prompt=prompt,
                response_model=DecomposeOutput,
                system_prompt="你是一个严谨的事实主张拆解器。不添加多余假设，忠实拆解用户原始输入。"
            )
            claims: List[Claim] = []
            for i, raw in enumerate(res.claims):
                claims.append(
                    Claim(
                        id=f"c-{uuid.uuid4().hex[:8]}",
                        original_input=input_text,
                        input_type=input_type,
                        statement=raw.statement,
                        claim_index=i,
                        attributes=ClaimAttributes(
                            subject=raw.subject,
                            predicate=raw.predicate,
                            object_value=raw.object_value,
                            time_context=raw.time_context,
                            polarity=raw.polarity
                        ),
                        verifiability=raw.verifiability,
                        verifiability_reason=raw.verifiability_reason or "根据陈述性质评估",
                        verified_as_of=today_str
                    )
                )
            return claims
        except Exception as e:
            logger.warning(f"Claim decomposition failed, using raw fallback: {e}")
            return [
                Claim(
                    id=f"c-{uuid.uuid4().hex[:8]}",
                    original_input=input_text,
                    input_type=input_type,
                    statement=input_text.strip(),
                    claim_index=0,
                    verifiability=Verifiability.PUBLICLY_VERIFIABLE,
                    verifiability_reason="单句直接核验",
                    verified_as_of=today_str
                )
            ]

    async def _verify_single_claim(self, claim: Claim, today_str: str) -> Verdict:
        """针对单个 Claim 执行检索、提取、溯源去重、规则引擎判定及解释生成"""
        # 1. 搜索来源
        search_query = claim.statement
        if claim.attributes and claim.attributes.subject:
            search_query = f"{claim.attributes.subject} {claim.attributes.predicate or ''} {claim.attributes.object_value or ''}".strip()
        
        search_results = await self.search.search(search_query, max_results=6)
        
        sources: List[Source] = []
        provenances: List[SourceProvenance] = []
        evidences: List[Evidence] = []

        for idx, item in enumerate(search_results):
            s_id = f"s-{idx+1}-{uuid.uuid4().hex[:4]}"
            url = getattr(item, "url", "#")
            title = getattr(item, "title", "Web Source")
            snippet = getattr(item, "snippet", "")
            domain = getattr(item, "domain", None)
            if not domain:
                domain = url.split("/")[2] if "://" in url else "web"
            tier = self._classify_source_tier(domain, url)
            
            source = Source(
                id=s_id,
                url=url,
                domain=domain,
                title=title,
                source_tier=tier,
                publish_date=getattr(item, "published_date", None) or today_str,
                is_synthetic=getattr(item, "is_synthetic", False)
            )
            sources.append(source)

        # 2. 从检索内容中提取证据
        if sources:
            all_snippets_text = "\n\n".join([
                f"[Source ID: {s.id} | {s.domain} | {s.title}]\n{s.title}\n{getattr(search_results[i], 'snippet', '')}"
                for i, s in enumerate(sources)
            ])

            extract_prompt = f"""针对待核验主张："{claim.statement}"
以下是检索到的公开网页摘要：
{all_snippets_text}

请提取与该主张直接相关、精确的证据片段。判断每条证据是支持 (supports_claim=true)、反驳 (contradicts_claim=true) 还是仅为背景上下文。
注意：
- 若内容提到'据 XX 消息'、'援引 XX 报道'，请在 origin_credit 中填入真实信源名称（如 'Bloomberg' 或 '公司官方声明'）。
- directness 标记为 DIRECT（直接证实或反驳）、INDIRECT（间接提及）或 CONTEXTUAL（背景说明）。
- scope_match 标记讨论事实与口径是否与待核验主张一致。"""

            try:
                ext_res: EvidenceExtractionBatch = await self.llm.generate_structured(
                    prompt=extract_prompt,
                    response_model=EvidenceExtractionBatch,
                    system_prompt="你是一个严谨的事实核验证据提取器。仅提取真实存在的文本片段，严格区分支持与反驳。"
                )
                for raw_ev in ext_res.evidences:
                    # 匹配所属 source
                    matched_s_id = sources[0].id
                    for s in sources:
                        if s.domain in raw_ev.exact_quote or s.title in raw_ev.exact_quote:
                            matched_s_id = s.id
                            break
                    
                    ev = Evidence(
                        id=f"e-{uuid.uuid4().hex[:6]}",
                        source_id=matched_s_id,
                        claim_id=claim.id,
                        exact_quote=raw_ev.exact_quote,
                        context=raw_ev.context,
                        supports_claim=raw_ev.supports_claim if not (raw_ev.supports_claim and raw_ev.contradicts_claim) else True,
                        contradicts_claim=raw_ev.contradicts_claim if not (raw_ev.supports_claim and raw_ev.contradicts_claim) else False,
                        directness=raw_ev.directness,
                        scope_match=raw_ev.scope_match,
                        evidence_note=raw_ev.evidence_note
                    )
                    evidences.append(ev)

                    # 记录信源溯源 (Canonical strict identity resolution)
                    if raw_ev.origin_credit:
                        resolved_origin_id = resolve_provenance_target(raw_ev.origin_credit, sources)
                        if resolved_origin_id and resolved_origin_id != matched_s_id:
                            provenances.append(
                                SourceProvenance(
                                    source_id=matched_s_id,
                                    origin_source_id=resolved_origin_id,
                                    provenance_type=ProvenanceType.CITES,
                                    explanation=f"引用自 {raw_ev.origin_credit}"
                                )
                            )
                        else:
                            # 严格单源隔离，不凭空捏造未被 manifest 收录的图谱节点 ID
                            logger.info(f"Provenance reference '{raw_ev.origin_credit}' isolated (not a tracked manifest source).")
            except Exception as e:
                # 抽取失败必须严格安全降级为 NO_VALID_EVIDENCE，绝不能伪造 supports_claim=True
                logger.warning(f"Evidence extraction failed or unresolvable: {e}. Defaulting to safe INSUFFICIENT state.")

        # 3. 运行确定性规则引擎
        assessment: EvidenceAssessment = assess_evidence_for_claim(
            claim=claim,
            sources=sources,
            evidences=evidences,
            provenances=provenances
        )
        evidence_state = compute_evidence_state(assessment, claim.verifiability)

        # 4. 生成人话解释清单 (why_reasons, evidence_gaps, next_step_advice)
        why_reasons, evidence_gaps, next_step_advice = await self._generate_verdict_explanation(
            claim=claim,
            assessment=assessment,
            evidence_state=evidence_state,
            sources=sources,
            evidences=evidences
        )

        return Verdict(
            claim_id=claim.id,
            evidence_state=evidence_state,
            why_reasons=why_reasons,
            evidence_gaps=evidence_gaps,
            next_step_advice=next_step_advice,
            verified_as_of=today_str
        )

    def _classify_source_tier(self, domain: str, url: str) -> SourceTier:
        """根据域名与 URL 快速归类来源类型"""
        d = domain.lower()
        if any(g in d for g in [".gov", "sec.gov", "samr.gov", ".edu", "court.gov"]):
            return SourceTier.OFFICIAL
        if any(o in d for o in ["reuters.com", "bloomberg.com", "apnews.com", "wsj.com", "ft.com", "xinhuanet.com", "cctv.com"]):
            return SourceTier.AUTHORITATIVE
        if any(m in d for m in ["36kr.com", "ithome.com", "thepaper.cn", "caixin.com", "sina.com.cn", "163.com", "qq.com"]):
            return SourceTier.MAINSTREAM
        if any(i in d for i in ["techcrunch.com", "huxiu.com", "geekpark.net", "infoq.cn", "csdn.net"]):
            return SourceTier.INDUSTRY
        if any(c in d for c in ["zhihu.com", "weibo.com", "reddit.com", "tieba.baidu.com", "x.com", "xiaohongshu.com"]):
            return SourceTier.COMMUNITY
        return SourceTier.UNKNOWN

    async def _generate_verdict_explanation(
        self,
        claim: Claim,
        assessment: EvidenceAssessment,
        evidence_state: EvidenceState,
        sources: List[Source],
        evidences: List[Evidence]
    ) -> tuple[List[str], List[str], str]:
        """由 LLM 将规则引擎判定的结论翻译为严谨、清晰的人话依据与建议"""
        prompt = f"""待核验声明: "{claim.statement}"
规则引擎计算判定状态: {evidence_state.value} ({evidence_state.name})
核验统计:
- 检索到来源总数: {assessment.total_sources_found}
- 经溯源去重独立信息源: {assessment.independent_source_count}
- 包含直接支持证据: {assessment.has_direct_support}
- 包含官方直接证实: {assessment.has_supporting_official_source}
- 包含可靠反证: {assessment.has_credible_contradicting_evidence}

已捕获证据摘要:
{json.dumps([{"quote": e.exact_quote, "supports": e.supports_claim, "contradicts": e.contradicts_claim, "directness": e.directness.value} for e in evidences[:4]], ensure_ascii=False)}

请生成清晰专业的核验解释：
1. why_reasons: 2 到 4 条判断依据清单，每条以 '✓' (支持) 或 '!' (存疑/反证) 或 'ℹ️' (信源属性) 开头
2. evidence_gaps: 1 到 2 条尚未找到的关键证据缺口（如 '尚未找到公司官方公告或工商变更记录'）
3. next_step_advice: 针对该事实类型给用户的具体核实指引（如 '如需进一步确认，建议查阅投资方公开披露或上市公司审计年报'）"""

        try:
            out: VerdictExplanationOutput = await self.llm.generate_structured(
                prompt=prompt,
                response_model=VerdictExplanationOutput,
                system_prompt="你是一个严谨的事实核验分析员。只客观陈述证据状态与来源情况，不下绝对真假断言。"
            )
            return out.why_reasons, out.evidence_gaps, out.next_step_advice
        except Exception:
            # 规则模板 fallback
            reasons = []
            if assessment.independent_source_count >= 2:
                reasons.append(f"✓ 找到 {assessment.independent_source_count} 个相互独立的信息源提及该事实")
            elif assessment.independent_source_count == 1:
                reasons.append("ℹ️ 仅有 1 个独立信息源提及，缺乏第三方多源交叉印证")
            else:
                reasons.append("! 公开检索未发现直接证实该说法的有效信息源")
            
            if assessment.has_supporting_official_source:
                reasons.append("✓ 获得官方/第一手权威渠道直接证实")
            if assessment.has_credible_contradicting_evidence:
                reasons.append("! 存在权威来源对该说法的关键数据或定性提出明确异议")

            gaps = ["尚未找到完整的第一手官方书面披露或审计归档"]
            advice = "目前建议将该说法列为待核验信息，可重点关注官方后续通告或权威监管备案。"
            return reasons, gaps, advice
