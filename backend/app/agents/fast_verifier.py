"""
AI Claim Verifier — Fast Verification Pipeline Agent (v4 Final)

执行单次快速事实核验：
1. Claim Decomposition (输入解析与多主张拆解)
2. Directed Search & Evidence Extraction (定向搜索与证据抽取)
3. Provenance Analysis (信息溯源与去重)
4. Rule Engine Verdict (确定性规则引擎判断)
5. Structured Explanation (清单式理由与缺口生成)
"""

import re
import json
import uuid
import asyncio
import hashlib
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

from app.models.reasoning_ir import (
    FactSlots,
    CompoundFactSlot,
    EvidenceRelation,
    RelationType,
    AccountingStandard,
    TemporalEvolution,
    ScopeAlignment,
    ReasoningAssessmentV2
)
from app.engine.reasoning_v2_engine import (
    compute_reasoning_v2_verdict,
    evaluate_compound_fact_fulfillment
)
from app.scraper.extractor import WebScraper

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  Structured LLM Output Schemas
# ──────────────────────────────────────────────

class RawCompoundSlot(BaseModel):
    slot_name: str = Field(description="属性或数值槽位名，如 'price', 'memory', 'lead_investor'")
    value: str = Field(description="属性值，如 '799', '16GB', 'Spark Capital'")
    unit: Optional[str] = Field(default=None, description="单位，如 'USD', 'GB', 'RMB'")
    is_required: bool = Field(default=True, description="是否为该主张成立所必需的属性")


class RawDecomposedClaim(BaseModel):
    statement: str = Field(description="拆解出的单条可独立核验的陈述句子")
    subject: Optional[str] = Field(default=None, description="主语实体，例如 'OpenAI'、'马斯克'")
    predicate: Optional[str] = Field(default=None, description="谓词动作/属性，例如 '融资'、'发布定价'")
    object_value: Optional[str] = Field(default=None, description="宾语/数值，例如 '10亿美元'、'799美元'")
    compound_slots: List[RawCompoundSlot] = Field(default_factory=list, description="多属性复合槽位列表")
    time_context: Optional[str] = Field(default=None, description="时间限定，例如 '2024年', 'Q3 2024'")
    accounting_basis: str = Field(default="UNKNOWN", description="会计准则口径: GAAP / NON_GAAP / UNKNOWN")
    trial_phase: Optional[str] = Field(default=None, description="临床试验阶段: PRELIMINARY / FINAL_CONFIRMED / UNKNOWN")
    polarity: bool = Field(default=True, description="极性: True=肯定句, False=否定句")
    verifiability: Verifiability = Field(default=Verifiability.PUBLICLY_VERIFIABLE, description="公开可验证性评级")
    verifiability_reason: str = Field(default="", description="为什么该声明具有此级别的公开可验证性")


class DecomposeOutput(BaseModel):
    claims: List[RawDecomposedClaim] = Field(description="拆解出的主张列表")


class RawExtractedEvidence(BaseModel):
    exact_quote: str = Field(description="原始网页中的精确原话或直接事实陈述")
    context: str = Field(default="", description="引文上下文")
    supports_claim: bool = Field(default=False, description="是否支持该主张")
    contradicts_claim: bool = Field(default=False, description="是否反驳/否定该主张")
    relation_type: str = Field(default="DIRECT_SUPPORT", description="关系类型: DIRECT_SUPPORT / QUALIFIED_CONFLICT / AUTHORITATIVE_REFUTE / DIRECT_CONTRADICT / INDIRECT_SUPPORT / CONTEXTUAL")
    accounting_standard: str = Field(default="UNKNOWN", description="证据体现的会计口径: GAAP / NON_GAAP / UNKNOWN")
    temporal_evolution: str = Field(default="CURRENT", description="证据时态/试验阶段: PRELIMINARY / FINAL_CONFIRMED / HISTORICAL_SUPERSEDED / CURRENT")
    matched_slots: List[str] = Field(default_factory=list, description="该证据直接匹配并证实的槽位名列表 (如 ['price', 'memory'])")
    directness: EvidenceDirectness = Field(default=EvidenceDirectness.CONTEXTUAL, description="直接性: DIRECT/INDIRECT/CONTEXTUAL")
    scope_match: bool = Field(default=True, description="讨论的事实和口径范围是否完全匹配")
    evidence_note: str = Field(default="", description="关键备注，例如口径差异或限制条件")
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

        # 2. 对每个拆解后的 Claim 并行执行定向证据检索与规则判定（最多 2 个核心主张并发）
        target_claims = claims[:2] if len(claims) > 2 else claims
        verdicts = list(await asyncio.gather(*(self._verify_single_claim(claim, today_str) for claim in target_claims)))

        # 3. 汇总生成多 Claim 整体覆盖状态
        coverage = generate_overall_coverage(
            original_input=input_text,
            input_type=input_type,
            claims=claims,
            verdicts=verdicts
        )
        return coverage

    def _build_directed_search_queries(self, claim: Claim, fact_slots: FactSlots) -> List[str]:
        """构建多路高信噪比定向搜索查询，结合原始语义、复合槽位与权威/争议修饰词"""
        queries: List[str] = []
        raw_entity = fact_slots.entity or (claim.attributes.subject if claim.attributes else "") or claim.statement[:20]
        
        # 提取核心实体（去除如 "及工作室"、"工作室"、"等人"、"团队"、"官方" 等修饰后缀以确保检索命中率）
        core_entity = raw_entity
        for suffix in ["及工作室", "工作室", "等人", "团队", "官方"]:
            if core_entity.endswith(suffix) and len(core_entity) > len(suffix):
                core_entity = core_entity[:-len(suffix)].strip()
                break

        # 1. 结构化实体 + 核心槽位数值 Query (过滤与实体重复项，保持紧凑 2~3 词最佳)
        slot_vals = [cs.value for cs in fact_slots.compound_slots if cs.value]
        time_ctx = fact_slots.time_context or ""
        distinct_slots = [v for v in slot_vals if v and v.lower() not in raw_entity.lower()]
        if distinct_slots:
            queries.append(f"{core_entity} {' '.join(distinct_slots[:2])}".strip())
        elif fact_slots.predicate and fact_slots.predicate != "statement":
            queries.append(f"{core_entity} {fact_slots.predicate}".strip())

        # 2. 争议/辟谣/回应/绯闻定向 Query (保持 2~3 个精准词)
        if not fact_slots.polarity or any(k in claim.statement for k in ["传闻", "出轨", "辟谣", "辞职", "否认", "被查", "涉嫌", "造谣", "绯闻", "风波"]):
            if any(k in claim.statement for k in ["辟谣", "造谣", "维权", "澄清"]):
                queries.append(f"{core_entity} 辟谣")
                queries.append(f"{core_entity} 声明 回应")
            elif any(k in claim.statement for k in ["出轨", "绯闻", "风波"]):
                queries.append(f"{core_entity} 出轨 绯闻")
            elif "辞职" in claim.statement:
                queries.append(f"{core_entity} 辞职 传闻")
            else:
                queries.append(f"{core_entity} 辟谣 声明")

        # 3. 官方/权威定向 Query
        if fact_slots.accounting_basis == AccountingStandard.GAAP:
            queries.append(f"{core_entity} {time_ctx} GAAP 财报 净利润".strip())
        elif any(cs.slot_name in ("price", "msrp", "memory") for cs in fact_slots.compound_slots):
            queries.append(f"{core_entity} {' '.join(distinct_slots[:2])} 建议零售价 规格".strip())
        elif any(cs.slot_name in ("founder", "founding_year", "headquarters") for cs in fact_slots.compound_slots):
            queries.append(f"{core_entity} 创始人 总部 创立时间".strip())
        else:
            queries.append(f"{core_entity} 官方公告 新闻稿".strip())

        # 4. 原始关键语义 Query (若原句过长则提炼关键词短语，避免整句送检0条结果)
        raw_clean = claim.statement.replace("网络传闻称", "").replace("据报道", "").strip()
        if len(raw_clean) <= 20:
            queries.append(raw_clean)
        else:
            parts = [p.strip() for p in re.split(r'[,，。；;、\s]+', raw_clean) if len(p.strip()) >= 2]
            short_q = " ".join(parts[:2])
            queries.append(short_q or raw_clean[:20])

        # 去重且保持顺序
        seen = set()
        unique_queries = []
        for q in queries:
            q_clean = q.strip()
            if q_clean and q_clean not in seen:
                seen.add(q_clean)
                unique_queries.append(q_clean)

        return unique_queries[:3]

    def _evaluate_search_result_relevance(
        self,
        item: Any,
        fact_slots: FactSlots,
        claim: Claim
    ) -> float:
        """评估检索结果与待核验主张的相关性得分 (0.0 ~ 1.0)，拦截风马牛不相及的垃圾网页（100% 动态无硬编码）"""
        if getattr(item, "is_synthetic", False):
            return 1.0

        title = (getattr(item, "title", "") or "").lower()
        snippet = (getattr(item, "snippet", "") or "").lower()
        url = (getattr(item, "url", "") or "").lower()
        combined = f"{title} {snippet} {url}"

        # 1. 动态提取核心实体 Stem Tokens
        raw_entity = (fact_slots.entity or (claim.attributes.subject if claim.attributes else "") or "").lower().strip()
        core_entity = raw_entity
        for suffix in ["及工作室", "工作室", "等人", "团队", "官方"]:
            if core_entity.endswith(suffix) and len(core_entity) > len(suffix):
                core_entity = core_entity[:-len(suffix)].strip()
                break

        entity_tokens = set()
        if core_entity:
            entity_tokens.add(core_entity)
            for tok in re.findall(r'[\u4e00-\u9fa5]{2,}|[a-z0-9]{3,}', core_entity):
                entity_tokens.add(tok)
        if raw_entity and raw_entity != core_entity:
            entity_tokens.add(raw_entity)

        entity_matched = any(token in combined for token in entity_tokens)

        # 2. 动态提取复合槽位与数值、关键约束词
        slot_tokens = set()
        for cs in fact_slots.compound_slots:
            if cs.value:
                slot_tokens.add(str(cs.value).lower().strip())

        # 从 Claim 语句中动态正则提取所有数字、金额、年份、代码与专有名词
        dyn_numbers = re.findall(r'\b\d+(?:\.\d+)?(?:%|gb|usd|亿|万|年|月|美元|元)?\b', claim.statement.lower())
        dyn_nouns = re.findall(r'[\u4e00-\u9fa5]{2,}|[a-z0-9]{3,}', claim.statement.lower())
        for tok in dyn_numbers + dyn_nouns:
            if tok and len(tok) >= 2 and tok not in entity_tokens:
                slot_tokens.add(tok)

        slot_hits = sum(1 for tok in slot_tokens if tok in combined)
        slot_ratio = (slot_hits / len(slot_tokens)) if slot_tokens else 0.5

        if entity_matched and slot_hits > 0:
            return 0.8 + 0.2 * min(slot_ratio, 1.0)
        elif entity_matched:
            return 0.5
        elif slot_hits >= 2:
            return 0.4
        else:
            return 0.05  # 极低相关度，判定为不相关

    async def _decompose_input(
        self,
        input_text: str,
        input_type: InputType,
        today_str: str
    ) -> List[Claim]:
        """将用户输入的一句话拆解为 1~N 个独立可验证事实，并强制覆盖所有属性约束"""
        prompt = f"""你是一个专业的事实核验系统的主张拆解器（Claim Decomposer）。
请分析用户输入的文本，将其拆解为 1 到 4 个独立、具体、可在互联网公开信息中独立检索验证的原子事实主张。
如果用户输入本身就是单一复合事实，请完整提取其所有属性约束。

【关键提取规则 - 严禁丢字段】：
1. 实体 subject: 准确识别主体公司或人物 (如 "英伟达", "Alphabet", "OpenAI", "Anthropic", "宇树科技")。
2. 谓词 predicate: 准确描述动作或核心属性 (如 "发布定价", "净利润", "订阅定价", "辞职卸任", "创立与总部")。
3. 复合槽位 compound_slots: 输入中出现的每一个数值、规格、金额、地点、人物、年份，必须全部提取为 compound_slots！
   - 硬件规格示例: [slot_name='model', value='RTX 4070 Ti Super'], [slot_name='price', value='799', unit='USD'], [slot_name='memory', value='16GB']
   - 财务示例: [slot_name='net_income', value='263.01', unit='亿美元']
   - 企业创立示例: [slot_name='headquarters', value='杭州'], [slot_name='founder', value='王兴兴'], [slot_name='founding_year', value='2016', unit='年']
4. 会计准则 accounting_basis: 若提及 GAAP / 非GAAP，准确填写 GAAP 或 NON_GAAP。
5. 极性 polarity: 若为传闻或辟谣（如传闻某人辞职），若该主张陈述的是该传闻动作，设为 True/False 保持逻辑一致。

输入文本: "{input_text}"

请输出结构化主张列表："""

        try:
            res: DecomposeOutput = await self.llm.generate_structured(
                prompt=prompt,
                response_model=DecomposeOutput,
                system_prompt="你是一个高精度事实主张拆解器。必须将输入文本中的所有实体、数值、地点、时间、年份与口径完整映射进 compound_slots。"
            )
            claims: List[Claim] = []
            for i, raw in enumerate(res.claims):
                compound_slots = [
                    CompoundFactSlot(
                        slot_name=cs.slot_name,
                        value=cs.value,
                        unit=cs.unit,
                        is_required=cs.is_required
                    )
                    for cs in getattr(raw, "compound_slots", [])
                ]
                accounting_basis = getattr(AccountingStandard, getattr(raw, "accounting_basis", "UNKNOWN").upper(), AccountingStandard.UNKNOWN)
                fact_slots = FactSlots(
                    entity=raw.subject or raw.statement[:20],
                    predicate=raw.predicate or "statement",
                    compound_slots=compound_slots,
                    time_context=raw.time_context,
                    accounting_basis=accounting_basis,
                    trial_phase=raw.trial_phase,
                    polarity=raw.polarity
                )

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
                        fact_slots=fact_slots,
                        verifiability=raw.verifiability,
                        verifiability_reason=raw.verifiability_reason,
                        verified_as_of=today_str
                    )
                )
            return claims
        except Exception as e:
            logger.warning(f"Claim decomposition failed: {e}. Falling back to single claim.")
            return []

    async def _verify_single_claim(self, claim: Claim, today_str: str) -> Verdict:
        """针对单个 Claim 执行多路定向检索、相关性过滤、正文抓取、物理定位及规则判定"""
        fact_slots: FactSlots = claim.fact_slots or FactSlots(
            entity=getattr(claim.attributes, "subject", None) or claim.statement[:20],
            predicate=getattr(claim.attributes, "predicate", None) or "statement",
            time_context=getattr(claim.attributes, "time_context", None),
            polarity=getattr(claim.attributes, "polarity", True)
        )

        # 1. 多路定向搜索
        queries = self._build_directed_search_queries(claim, fact_slots)
        search_results: List[Any] = []
        seen_urls = set()

        for q in queries:
            try:
                sub_res = await self.search.search(q, max_results=4)
                for item in sub_res:
                    u = getattr(item, "url", "")
                    if u and u not in seen_urls:
                        seen_urls.add(u)
                        search_results.append(item)
            except Exception as e:
                logger.warning(f"Search query '{q}' failed: {e}")

        # 若多路未返回，保底使用原始 statement 搜索
        if not search_results:
            search_results = await self.search.search(claim.statement, max_results=5)

        sources: List[Source] = []
        provenances: List[SourceProvenance] = []
        evidences: List[Evidence] = []
        relations: List[EvidenceRelation] = []

        for idx, item in enumerate(search_results):
            s_id = f"s-{idx+1}-{uuid.uuid4().hex[:4]}"
            url = getattr(item, "url", "#")
            title = getattr(item, "title", "Web Source")
            snippet = getattr(item, "snippet", "")
            domain = getattr(item, "domain", None)
            if not domain:
                domain = url.split("/")[2] if "://" in url else "web"
            tier = self._classify_source_tier(domain, url)

            # 相关性闸门检查 (Pre-Scrape Relevance Gate)
            relevance_score = self._evaluate_search_result_relevance(item, fact_slots, claim)
            
            raw_text = None
            content_hash = None
            fetch_status = "FETCH_FAILED"
            fetch_mode = "LIVE"

            if relevance_score < 0.2 and not getattr(item, "is_synthetic", False):
                # 过滤无关网页，避免垃圾噪音注入
                fetch_status = "REJECTED_IRRELEVANT"
                logger.info(f"Rejected irrelevant search result: {title} ({url}) score={relevance_score}")
            elif getattr(item, "is_synthetic", False):
                raw_text = snippet
                content_hash = hashlib.sha256(snippet.encode("utf-8")).hexdigest()
                fetch_status = "SYNTHETIC_MOCK"
                fetch_mode = "SYNTHETIC"
            elif url.startswith("http"):
                try:
                    scraped = await WebScraper.fetch_and_extract(url, timeout_seconds=10)
                    if scraped and scraped.clean_text:
                        raw_text = scraped.clean_text
                        content_hash = scraped.content_hash
                        fetch_status = "FETCH_SUCCESS"
                        fetch_mode = "LIVE"
                    else:
                        fetch_status = "FETCH_EMPTY"
                        fetch_mode = "LIVE"
                except Exception as e:
                    logger.warning(f"Live fetch failed for {url}: {e}")
                    fetch_status = "FETCH_FAILED"
                    fetch_mode = "LIVE"
            
            source = Source(
                id=s_id,
                url=url,
                domain=domain,
                title=title,
                source_tier=tier,
                publish_date=getattr(item, "published_date", None) or today_str,
                is_synthetic=getattr(item, "is_synthetic", False),
                raw_text=raw_text,
                content_hash=content_hash,
                fetch_status=fetch_status,
                fetch_mode=fetch_mode
            )
            sources.append(source)

        # 2. 从检索内容中提取证据与 V2 关系
        sources_with_text = [s for s in sources if s.raw_text]
        if sources_with_text:
            all_snippets_text = "\n\n".join([
                f"[Source ID: {s.id} | {s.domain} | {s.title}]\n{s.title}\n{(s.raw_text or '')[:1500]}"
                for s in sources_with_text
            ])

            slot_names_str = ", ".join([f"{cs.slot_name}='{cs.value}'" for cs in fact_slots.compound_slots]) or "无复合槽位"

            extract_prompt = f"""针对待核验主张："{claim.statement}"
主张核心实体：{fact_slots.entity}，谓词：{fact_slots.predicate}，复合属性槽位：[{slot_names_str}]

以下是检索到的公开网页正文内容：
{all_snippets_text}

请提取与该主张直接相关、精确的证据片段，并完成关系分类：
1. exact_quote: 原始网页正文中真实存在的逐字原话 (严禁凭空编写或概括)。
2. relation_type:
   - DIRECT_SUPPORT: 直接证实主张及其复合槽位
   - QUALIFIED_CONFLICT: 存在合法口径分歧(如GAAP vs Non-GAAP)或时序演进(如临床一期 vs 三期)
   - AUTHORITATIVE_REFUTE: 官方一手声明明确辟谣或监管机构直接否定
   - DIRECT_CONTRADICT: 存在确定性的事实或数值冲突
   - INDIRECT_SUPPORT: 二次转述或弱相关支持
   - CONTEXTUAL: 背景说明
3. accounting_standard: 若体现财务准则，填写 GAAP / NON_GAAP / UNKNOWN
4. temporal_evolution: 若涉及试验时态，填写 PRELIMINARY / FINAL_CONFIRMED / CURRENT
5. matched_slots: 填写该引文实际匹配证实的槽位名称列表
6. origin_credit: 若内容提到'据 XX 消息'，填写真实源头名称。"""

            try:
                ext_res: EvidenceExtractionBatch = await self.llm.generate_structured(
                    prompt=extract_prompt,
                    response_model=EvidenceExtractionBatch,
                    system_prompt="你是一个严谨的事实核验证据与语义关系提取器。仅提取真实存在的文本，严格区分支持与反驳。"
                )
                for raw_ev in ext_res.evidences:
                    # 匹配所属 source
                    matched_s = sources_with_text[0]
                    for s in sources_with_text:
                        if (s.raw_text and raw_ev.exact_quote in s.raw_text) or s.domain in raw_ev.exact_quote or s.title in raw_ev.exact_quote:
                            matched_s = s
                            break
                    
                    # 物理 Raw-Text 定位校验
                    char_start, char_end, prefix, suffix, match_tier, el_role, blk_id = WebScraper.locate_quote_spans(
                        source_text=matched_s.raw_text or "",
                        quote=raw_ev.exact_quote
                    )

                    # 严格准入闸门：仅允许 EXACT 或 NORMALIZED_EXACT 作为有效事实依据
                    is_grounded = match_tier in ("EXACT", "NORMALIZED_EXACT")

                    ev = Evidence(
                        id=f"e-{uuid.uuid4().hex[:6]}",
                        source_id=matched_s.id,
                        claim_id=claim.id,
                        exact_quote=raw_ev.exact_quote,
                        context=raw_ev.context,
                        supports_claim=raw_ev.supports_claim if is_grounded else False,
                        contradicts_claim=raw_ev.contradicts_claim if is_grounded else False,
                        directness=raw_ev.directness,
                        scope_match=raw_ev.scope_match,
                        evidence_note=raw_ev.evidence_note,
                        char_start=char_start,
                        char_end=char_end,
                        match_tier=match_tier,
                        prefix=prefix,
                        suffix=suffix,
                        is_admissible_factual_evidence=is_grounded,
                        element_role=el_role,
                        block_id=blk_id
                    )
                    evidences.append(ev)

                    # 构建并校验 EvidenceRelation
                    rel_type = getattr(RelationType, getattr(raw_ev, "relation_type", "DIRECT_SUPPORT").upper(), RelationType.DIRECT_SUPPORT)
                    acc_std = getattr(AccountingStandard, getattr(raw_ev, "accounting_standard", "UNKNOWN").upper(), AccountingStandard.UNKNOWN)
                    temp_evo = getattr(TemporalEvolution, getattr(raw_ev, "temporal_evolution", "CURRENT").upper(), TemporalEvolution.CURRENT)
                    
                    # 校验 matched_slots 是否真实存在于 FactSlots 中 (IR 完整性校验)
                    valid_slot_names = {cs.slot_name for cs in fact_slots.compound_slots}
                    filtered_matched_slots = [slot for slot in getattr(raw_ev, "matched_slots", []) if slot in valid_slot_names]

                    relations.append(
                        EvidenceRelation(
                            relation_type=rel_type,
                            accounting_standard=acc_std,
                            temporal_evolution=temp_evo,
                            matched_slots=filtered_matched_slots,
                            polarity_reasoning=getattr(raw_ev, "evidence_note", "")
                        )
                    )

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

        multi_round_audit = {
            "round_count": 1,
            "initial_state": evidence_state.value,
            "final_state": evidence_state.value,
            "resolved_gaps": []
        }

        # 5. 【Autonomous Evidence-Gap Investigation Loop】
        # 若第一轮由于单源、缺少官方确认或证据不足落入 INSUFFICIENT，且存在明确证据缺口，则自动发起第 2 轮定向缺口检索
        if evidence_state == EvidenceState.INSUFFICIENT and evidence_gaps and len(sources) > 0:
            logger.info(f"[Autonomous Loop] Claim '{claim.statement[:30]}' is INSUFFICIENT. Triggering Round 2 with gaps: {evidence_gaps}")
            gap_query = self._generate_gap_targeted_query(claim, evidence_gaps)
            round_2_results = await self.search.search(gap_query, max_results=4)
            
            existing_urls = {s.url for s in sources}
            new_sources: List[Source] = []
            
            for idx, item in enumerate(round_2_results):
                url = getattr(item, "url", "#")
                if url in existing_urls:
                    continue
                s_id = f"s-r2-{idx+1}-{uuid.uuid4().hex[:4]}"
                title = getattr(item, "title", "Web Source (R2)")
                snippet = getattr(item, "snippet", "")
                domain = getattr(item, "domain", None)
                if not domain:
                    domain = url.split("/")[2] if "://" in url else "web"
                tier = self._classify_source_tier(domain, url)
                
                # 相关性闸门检查 (Pre-Scrape Relevance Gate)
                relevance_score = self._evaluate_search_result_relevance(item, fact_slots, claim)
                raw_text = None
                content_hash = None
                fetch_status = "FETCH_FAILED"
                fetch_mode = "LIVE"

                if relevance_score < 0.2 and not getattr(item, "is_synthetic", False):
                    fetch_status = "REJECTED_IRRELEVANT"
                    logger.info(f"[R2] Rejected irrelevant search result: {title} ({url}) score={relevance_score}")
                elif getattr(item, "is_synthetic", False):
                    raw_text = snippet
                    content_hash = hashlib.sha256(snippet.encode("utf-8")).hexdigest()
                    fetch_status = "SYNTHETIC_MOCK"
                    fetch_mode = "SYNTHETIC"
                elif url.startswith("http"):
                    try:
                        scraped = await WebScraper.fetch_and_extract(url, timeout_seconds=10)
                        if scraped and scraped.clean_text:
                            raw_text = scraped.clean_text
                            content_hash = scraped.content_hash
                            fetch_status = "FETCH_SUCCESS"
                            fetch_mode = "LIVE"
                        else:
                            fetch_status = "FETCH_EMPTY"
                            fetch_mode = "LIVE"
                    except Exception as e:
                        logger.warning(f"Round 2 live fetch failed for {url}: {e}")
                        fetch_status = "FETCH_FAILED"
                        fetch_mode = "LIVE"

                source = Source(
                    id=s_id,
                    url=url,
                    domain=domain,
                    title=title,
                    source_tier=tier,
                    publish_date=getattr(item, "published_date", None) or today_str,
                    is_synthetic=getattr(item, "is_synthetic", False),
                    raw_text=raw_text,
                    content_hash=content_hash,
                    fetch_status=fetch_status,
                    fetch_mode=fetch_mode
                )
                new_sources.append(source)
                sources.append(source)
                existing_urls.add(url)

            # 仅在抓取到真实正文时提取证据与物理定位
            sources_with_text_r2 = [s for s in new_sources if s.raw_text]
            if sources_with_text_r2:
                all_snippets_text_r2 = "\n\n".join([
                    f"[Source ID: {s.id} | {s.domain} | {s.title}]\n{s.title}\n{(s.raw_text or '')[:1500]}"
                    for s in sources_with_text_r2
                ])

                r2_prompt = f"""针对待核验主张："{claim.statement}"
第一轮调查发现存在以下关键证据缺口：{'; '.join(evidence_gaps)}
以下是从抓取网页正文中检索到的补充证据材料：
{all_snippets_text_r2}

请提取能够弥补上述缺口、直接支持或反驳该主张的精确逐字证据片段。"""

                try:
                    ext_res_r2: EvidenceExtractionBatch = await self.llm.generate_structured(
                        prompt=r2_prompt,
                        response_model=EvidenceExtractionBatch,
                        system_prompt="你是一个严谨的事实核验证据提取器。必须直接从正文中提取逐字原文引文，严禁改写或捏造。"
                    )
                    for raw_ev in ext_res_r2.evidences:
                        matched_s = sources_with_text_r2[0]
                        for s in sources_with_text_r2:
                            if s.domain in raw_ev.exact_quote or s.title in raw_ev.exact_quote:
                                matched_s = s
                                break
                        
                        # 物理引文坐标定位 (Physical Quote Grounding)
                        char_start, char_end, prefix, suffix, match_tier, el_role, blk_id = WebScraper.locate_quote_spans(
                            source_text=matched_s.raw_text or "",
                            quote=raw_ev.exact_quote
                        )

                        is_grounded = match_tier in ("EXACT", "NORMALIZED_EXACT")
                        is_admissible = is_grounded or matched_s.is_synthetic

                        supports = raw_ev.supports_claim if is_grounded else False
                        contradicts = raw_ev.contradicts_claim if is_grounded else False
                        if supports and contradicts:
                            supports = True
                            contradicts = False

                        ev = Evidence(
                            id=f"e-r2-{uuid.uuid4().hex[:6]}",
                            source_id=matched_s.id,
                            claim_id=claim.id,
                            exact_quote=raw_ev.exact_quote,
                            context=raw_ev.context,
                            supports_claim=supports,
                            contradicts_claim=contradicts,
                            directness=raw_ev.directness,
                            scope_match=raw_ev.scope_match,
                            evidence_note=raw_ev.evidence_note,
                            char_start=char_start,
                            char_end=char_end,
                            prefix=prefix,
                            suffix=suffix,
                            match_tier=match_tier,
                            is_admissible_factual_evidence=is_admissible,
                            element_role=el_role,
                            block_id=blk_id
                        )
                        evidences.append(ev)

                        if is_grounded:
                            rel_type = getattr(RelationType, getattr(raw_ev, "relation_type", "DIRECT_SUPPORT").upper(), RelationType.DIRECT_SUPPORT)
                            acc_std = getattr(AccountingStandard, getattr(raw_ev, "accounting_standard", "UNKNOWN").upper(), AccountingStandard.UNKNOWN)
                            temp_evo = getattr(TemporalEvolution, getattr(raw_ev, "temporal_evolution", "CURRENT").upper(), TemporalEvolution.CURRENT)
                            valid_slot_names = {cs.slot_name for cs in fact_slots.compound_slots}
                            filtered_matched_slots = [slot for slot in getattr(raw_ev, "matched_slots", []) if slot in valid_slot_names]

                            relations.append(
                                EvidenceRelation(
                                    relation_type=rel_type,
                                    accounting_standard=acc_std,
                                    temporal_evolution=temp_evo,
                                    matched_slots=filtered_matched_slots,
                                    polarity_reasoning=getattr(raw_ev, "evidence_note", "")
                                )
                            )
                except Exception as e:
                    logger.warning(f"Round 2 extraction failed: {e}")

                # 重新评估合并证据集 (仅使用已物理验证的准入证据)
                assessment = assess_evidence_for_claim(
                    claim=claim,
                    sources=sources,
                    evidences=[e for e in evidences if e.is_admissible_factual_evidence],
                    provenances=provenances
                )
                evidence_state = compute_evidence_state(assessment, claim.verifiability)
                
                # 重新生成解释与剩余缺口
                why_reasons, evidence_gaps, next_step_advice = await self._generate_verdict_explanation(
                    claim=claim,
                    assessment=assessment,
                    evidence_state=evidence_state,
                    sources=sources,
                    evidences=evidences
                )

                multi_round_audit = {
                    "round_count": 2,
                    "initial_state": "INSUFFICIENT",
                    "final_state": evidence_state.value,
                    "gap_query": gap_query,
                    "new_sources_added": len(new_sources),
                    "state_elevated": (evidence_state != EvidenceState.INSUFFICIENT)
                }

        return Verdict(
            claim_id=claim.id,
            evidence_state=evidence_state,
            why_reasons=why_reasons,
            evidence_gaps=evidence_gaps,
            next_step_advice=next_step_advice,
            verified_as_of=today_str,
            assessment=assessment,
            sources=sources,
            evidences=evidences,
            provenances=provenances,
            fact_slots=fact_slots,
            relations=relations,
            multi_round_audit=multi_round_audit
        )

    def _generate_gap_targeted_query(self, claim: Claim, gaps: List[str]) -> str:
        """根据证据缺口生成定向搜索关键词"""
        base = claim.statement
        gap_str = " ".join(gaps)
        if any(kw in gap_str for kw in ["官方", "公告", "声明"]):
            return f"{base} 官方公告 声明"
        elif any(kw in gap_str for kw in ["SEC", "财报", "10-Q"]):
            return f"{base} SEC filing 10-Q"
        elif any(kw in gap_str for kw in ["独立", "第三方", "证实"]):
            return f"{base} Reuters Bloomberg 权威报道"
        return f"{base} 证实 辟谣 声明"

    def _classify_source_tier(self, domain: str, url: str) -> SourceTier:
        """根据域名与 URL 快速归类来源类型"""
        d = domain.lower()
        if any(g in d for g in [".gov", "sec.gov", "samr.gov", ".edu", "court.gov"]):
            return SourceTier.OFFICIAL
        if any(o in d for o in ["reuters.com", "bloomberg.com", "apnews.com", "wsj.com", "ft.com", "xinhuanet.com", "cctv.com", "people.com.cn"]):
            return SourceTier.AUTHORITATIVE
        if any(m in d for m in ["36kr.com", "ithome.com", "thepaper.cn", "caixin.com", "sina.com.cn", "sina.cn", "163.com", "qq.com", "sohu.com", "ifeng.com", "msn.com", "msn.cn", "jiemian.com", "zaobao.com"]):
            return SourceTier.MAINSTREAM
        if any(i in d for i in ["techcrunch.com", "huxiu.com", "geekpark.net", "infoq.cn", "csdn.net"]):
            return SourceTier.INDUSTRY
        if any(c in d for c in ["zhihu.com", "weibo.com", "weibo.cn", "reddit.com", "tieba.baidu.com", "x.com", "xiaohongshu.com", "douban.com", "bilibili.com", "baijiahao.baidu.com"]):
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
