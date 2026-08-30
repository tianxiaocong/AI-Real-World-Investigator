import hashlib
import json
from typing import Optional, Type, TypeVar
from pydantic import BaseModel
from app.providers.llm.base import LLMProvider
from app.models.schemas import (
    ResearchPlan, TargetType, SubTask
)

T = TypeVar("T", bound=BaseModel)

class MockLLMProvider(LLMProvider):
    """Mock LLM provider for local offline testing and unit tests"""

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> str:
        return f"[Mock Response for prompt: {prompt[:80]}...]"

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
    ) -> T:
        import re
        from app.agents.claim_extractor import ClaimExtractionBatch, RawExtractedClaim
        from app.agents.verifier import ConflictJudgement
        from app.agents.synthesizer import StructuredSynthesisOutput
        from app.models.schemas import ClaimType, ConfidenceLevel

        # Extract target query name from prompt if present
        target_name = "调查目标"
        m = re.search(r'(?:Investigation Target|目标)[：:\s]*["\']?([^"\'\n\r]+)["\']?', prompt, re.IGNORECASE)
        if m:
            target_name = m.group(1).strip()

        is_unitree = any(k in target_name for k in ["宇树", "Unitree", "机器人", "王兴兴"])

        # Extract target type hint if present in prompt
        t_type = TargetType.COMPANY
        for tt in TargetType:
            if tt.value in prompt.upper():
                t_type = tt
                break

        # 1. Research Plan
        if response_model == ResearchPlan:
            if is_unitree:
                return ResearchPlan(
                    target_type=TargetType.COMPANY,
                    target_name=target_name,
                    key_hypotheses=[
                        "四足与通用人形机器人商业化量产处于全球第一梯队，率先将人形机器人价格打入 10 万元以内区间。",
                        "在关节电机与动力学算法上具备成本与自研优势，但在复杂具身大模型泛化与长程任务操作上仍有待突破。"
                    ],
                    sub_tasks=[
                        SubTask(
                            id="task-1",
                            dimension="公司背景与创始人架构",
                            question="宇树科技创始人王兴兴的创业履历、创始团队背景与核心控制权架构如何？",
                            search_queries=["宇树科技 创始人 王兴兴 履历", "宇树科技 股权架构 核心团队"],
                            rationale="理清核心创始团队的技术基因与公司治理结构。"
                        ),
                        SubTask(
                            id="task-2",
                            dimension="融资历程与估值财务",
                            question="宇树科技 2024-2026 年最新融资轮次、投资方阵营（美团/深创投/红杉）与估值如何？",
                            search_queries=["宇树科技 B2轮 融资 美团 深创投", "宇树科技 估值 营收 财务数据"],
                            rationale="核验真实资本实力与商业化营收体量。"
                        ),
                        SubTask(
                            id="task-3",
                            dimension="产品矩阵与真实技术评测",
                            question="四足机器人（B2/Go2）与人形机器人（H1/G1）的真实评测表现、量产定价与行业竞争优劣势？",
                            search_queries=["宇树 G1 人形机器人 9.9万 评测", "宇树科技 H1 机器人 优劣势 争议"],
                            rationale="剥离营销宣传，评估真实技术护城河与潜在缺陷。"
                        ),
                    ]
                )  # type: ignore
            elif t_type == TargetType.PRODUCT:
                return ResearchPlan(
                    target_type=TargetType.PRODUCT,
                    target_name=target_name,
                    key_hypotheses=[
                        f"{target_name} 在核心性能指标上表现亮眼，但用户在真实使用场景中反映存在散热或续航短板。",
                        f"{target_name} 的定价策略主打高端市场，面临同类竞品高性价比替代的竞争压力。"
                    ],
                    sub_tasks=[
                        SubTask(
                            id="task-1",
                            dimension="硬件参数与基准实测",
                            question=f"{target_name} 的核心规格参数与第三方评测跑分表现如何？",
                            search_queries=[f"{target_name} 参数 实测 跑分", f"{target_name} 规格 对比"],
                            rationale="获取客观硬件基准与性能数据。"
                        ),
                        SubTask(
                            id="task-2",
                            dimension="真实口碑与故障率",
                            question=f"{target_name} 在长期使用中的发热、续航、故障与用户投诉集中在哪些方面？",
                            search_queries=[f"{target_name} 缺点 发热 续航 翻车", f"{target_name} 故障率 售后 评价"],
                            rationale="排查营销滤镜下的真实使用体验缺陷。"
                        ),
                        SubTask(
                            id="task-3",
                            dimension="竞品横评与性价比",
                            question=f"{target_name} 与同赛道核心竞品相比的优劣势及价格定位如何？",
                            search_queries=[f"{target_name} 竞品 对比 推荐", f"{target_name} 性价比 评测"],
                            rationale="综合评估产品竞争力和购买决策建议。"
                        )
                    ]
                )  # type: ignore
            elif t_type == TargetType.INVESTMENT:
                return ResearchPlan(
                    target_type=TargetType.INVESTMENT,
                    target_name=target_name,
                    key_hypotheses=[
                        f"{target_name} 宣称的高年化回报率存在资金池运转与信息披露不透明风险。",
                        f"{target_name} 缺乏权威金融监管牌照，底层资产与造血机制存疑。"
                    ],
                    sub_tasks=[
                        SubTask(
                            id="task-1",
                            dimension="商业模式与底层造血",
                            question=f"{target_name} 的资金投向、收益产生来源与商业闭环是否真实成立？",
                            search_queries=[f"{target_name} 商业模式 底层资产", f"{target_name} 收益来源 造血"],
                            rationale="验证收益来源的真实性与合规性。"
                        ),
                        SubTask(
                            id="task-2",
                            dimension="合规资质与监管排查",
                            question=f"{target_name} 及其运营主体是否具备对应金融牌照或存在监管风险通报？",
                            search_queries=[f"{target_name} 金融牌照 监管 备案", f"{target_name} 涉嫌 非法集资 预警"],
                            rationale="排查非法集资与虚假宣传法律风险。"
                        ),
                        SubTask(
                            id="task-3",
                            dimension="资方背景与兑付历史",
                            question=f"{target_name} 的股东资方实力如何，过往兑付是否出现延迟或违约？",
                            search_queries=[f"{target_name} 股东 资方 兑付 违约", f"{target_name} 投诉 维权"],
                            rationale="评估信用违约与流动性崩塌风险。"
                        )
                    ]
                )  # type: ignore
            elif t_type == TargetType.CLAIM:
                return ResearchPlan(
                    target_type=TargetType.CLAIM,
                    target_name=target_name,
                    key_hypotheses=[
                        f"关于「{target_name}」的传言存在断章取义或营销夸大成分。",
                        f"权威官方声明与第三方独立核验机构已对此传言做出明确澄清或反驳。"
                    ],
                    sub_tasks=[
                        SubTask(
                            id="task-1",
                            dimension="传言原始出处溯源",
                            question=f"关于「{target_name}」的最早信源出处、首发时间与初始传播文本是什么？",
                            search_queries=[f"{target_name} 原始出处 首发 来源", f"{target_name} 传言 起源"],
                            rationale="追踪信息源头，判断是否为自媒体恶意拼凑。"
                        ),
                        SubTask(
                            id="task-2",
                            dimension="当事方官方通报与声明",
                            question=f"相关主体、官方机构或当事人是否发布过正式辟谣声明或澄清公告？",
                            search_queries=[f"{target_name} 官方通报 辟谣 声明", f"{target_name} 警方通报 真相"],
                            rationale="获取第一手权威官方定论。"
                        ),
                        SubTask(
                            id="task-3",
                            dimension="事实链条反证与矛盾点",
                            question=f"是否存在与「{target_name}」相互矛盾的时间线证据或物证记录？",
                            search_queries=[f"{target_name} 证据 矛盾 疑点", f"{target_name} 反转 真相 调查"],
                            rationale="建立完整的正反反证事实链。"
                        )
                    ]
                )  # type: ignore
            elif t_type == TargetType.TECHNOLOGY:
                return ResearchPlan(
                    target_type=TargetType.TECHNOLOGY,
                    target_name=target_name,
                    key_hypotheses=[
                        f"{target_name} 在实验室理论阶段已获验证，但大规模工业化量产面临良品率与成本壁垒。",
                        f"{target_name} 存在部分宣传概念前置超前，实际商用落地周期长于预期。"
                    ],
                    sub_tasks=[
                        SubTask(
                            id="task-1",
                            dimension="底层科学原理与专利",
                            question=f"{target_name} 的核心底层理论、学术论文支撑与核心专利储备如何？",
                            search_queries=[f"{target_name} 原理 论文 专利", f"{target_name} 技术路线 突破"],
                            rationale="验证技术底座的科学性与自主知识产权。"
                        ),
                        SubTask(
                            id="task-2",
                            dimension="产业化壁垒与良品率",
                            question=f"{target_name} 在工程化落地、良品率、生产成本与供应链上面临哪些关键瓶颈？",
                            search_queries=[f"{target_name} 量产 瓶颈 良品率 成本", f"{target_name} 商业化 挑战"],
                            rationale="剥离实验室噱头，评估真实落地难度。"
                        ),
                        SubTask(
                            id="task-3",
                            dimension="权威评测与宣传对比",
                            question=f"第三方权威科研机构或 Benchmark 实测是否验证了 {target_name} 的公开宣称数据？",
                            search_queries=[f"{target_name} Benchmark 实测 夸大", f"{target_name} 真实 表现 质疑"],
                            rationale="甄别技术宣发是否存在夸大造假。"
                        )
                    ]
                )  # type: ignore
            else:
                return ResearchPlan(
                    target_type=TargetType.COMPANY,
                    target_name=target_name,
                    key_hypotheses=[
                        f"{target_name} 在 2024-2026 年保持活跃的商业运营与技术迭代。",
                        f"行业竞争格局加剧背景下，{target_name} 面临产品交付与供应链成本优化挑战。"
                    ],
                    sub_tasks=[
                        SubTask(
                            id="task-1",
                            dimension="组织治理与核心背景",
                            question=f"{target_name} 的创立背景、关键管理层与发展里程碑？",
                            search_queries=[f"{target_name} 创始人 管理层 历史", f"{target_name} 官方架构"],
                            rationale="厘清主体基本面。"
                        ),
                        SubTask(
                            id="task-2",
                            dimension="财务状况与商业化",
                            question=f"{target_name} 的最新融资、商业模式与营收规模？",
                            search_queries=[f"{target_name} 融资 估值 财务数据", f"{target_name} 商业模式"],
                            rationale="评估商业健康度与盈利可持续性。"
                        ),
                        SubTask(
                            id="task-3",
                            dimension="争议与潜在风险",
                            question=f"{target_name} 是否存在公开法律诉讼、行业竞争争议或用户负面反馈？",
                            search_queries=[f"{target_name} 争议 风险 投诉", f"{target_name} 竞品对比 短板"],
                            rationale="排查潜在隐患与未验证信息。"
                        ),
                    ]
                )  # type: ignore

        # 2. Claim Extraction
        if response_model == ClaimExtractionBatch:
            if is_unitree:
                return ClaimExtractionBatch(
                    claims=[
                        RawExtractedClaim(
                            statement="宇树科技于2024年完成近10亿元人民币B2轮融资，由美团、金石投资、深创投联合领投，红杉中国跟投。",
                            exact_quote="宣布完成近10亿元人民币B2轮融资，由美团、金石投资、深创投联合领投",
                            claim_type=ClaimType.FACT_STATEMENT,
                            confidence=ConfidenceLevel.HIGH,
                            reasoning="由36氪等权威财经媒体及资方联合披露。"
                        ),
                        RawExtractedClaim(
                            statement="宇树科技由CEO王兴兴于2016年创立，核心产品线覆盖四足机器人（Go2、B2）与全尺寸通用人形机器人（H1、G1）。",
                            exact_quote="由CEO王兴兴于2016年创立，总部位于杭州。核心产品线覆盖工业级与消费级四足机器人",
                            claim_type=ClaimType.FACT_STATEMENT,
                            confidence=ConfidenceLevel.HIGH,
                            reasoning="官方公司架构与技术路线图明确记载。"
                        ),
                        RawExtractedClaim(
                            statement="宇树全尺寸通用人形机器人G1官方定价为9.9万元人民币起，开创人形机器人规模化平价量产先河。",
                            exact_quote="全尺寸人形机器人G1定价9.9万元起，实现了人形机器人行业规模化商业量产",
                            claim_type=ClaimType.FACT_STATEMENT,
                            confidence=ConfidenceLevel.HIGH,
                            reasoning="官方公开发布会及官网上线售价。"
                        ),
                        RawExtractedClaim(
                            statement="行业专家指出宇树在低价策略下的综合硬件毛利率承压，且复杂灵巧手精细操作大模型数据仍显不足。",
                            exact_quote="但在双足人形机器人复杂灵巧手抓取操作与具身大模型算法泛化上，仍面临数据收集不足",
                            claim_type=ClaimType.OPINION,
                            confidence=ConfidenceLevel.MEDIUM,
                            reasoning="知乎与行业评测专家深度剖析观点。"
                        )
                    ]
                )  # type: ignore
            else:
                return ClaimExtractionBatch(
                    claims=[
                        RawExtractedClaim(
                            statement=f"{target_name} 在 2024-2025 年间保持跨越式增长，年营收规模与商业化落地稳步推进。",
                            exact_quote="实现了核心业务跨越式增长，年营收规模与商业化落地稳步推进",
                            claim_type=ClaimType.FACT_STATEMENT,
                            confidence=ConfidenceLevel.HIGH,
                            reasoning="行业综合调研报告披露。"
                        ),
                        RawExtractedClaim(
                            statement=f"{target_name} 保持合规稳健运营，已在全球设立多处研发与运营中心。",
                            exact_quote="保持合规稳健运营，已在全球设立多处研发与运营中心",
                            claim_type=ClaimType.FACT_STATEMENT,
                            confidence=ConfidenceLevel.HIGH,
                            reasoning="官方监管与备案记录。"
                        ),
                        RawExtractedClaim(
                            statement=f"部分社区用户对 {target_name} 高端产品交付周期及售后支持生态提出了改进建议。",
                            exact_quote="针对其高端产品交付周期与售后支持生态提出了部分改进建议",
                            claim_type=ClaimType.OPINION,
                            confidence=ConfidenceLevel.MEDIUM,
                            reasoning="社区评测讨论与用户反馈。"
                        )
                    ]
                )  # type: ignore

        # 3. Conflict Judgement
        if response_model == ConflictJudgement:
            return ConflictJudgement(
                is_conflicting=False,
                is_supporting=True,
                explanation="来源彼此印证，描述了同一技术与商业发展脉络。"
            )  # type: ignore

        # 5. Fast Claim Verification Pipeline Models
        if response_model.__name__ == "DecomposeOutput":
            from app.agents.fast_verifier import DecomposeOutput, RawDecomposedClaim, RawCompoundSlot
            from app.models.verification_models import Verifiability

            if "RTX 4070" in prompt:
                return DecomposeOutput(
                    claims=[
                        RawDecomposedClaim(
                            statement="英伟达 GeForce RTX 4070 Ti Super 建议零售价为799美元，配备16GB GDDR6X显存",
                            subject="Nvidia RTX 4070 Ti Super",
                            predicate="hardware_spec_pricing",
                            object_value="799美元 16GB",
                            compound_slots=[
                                RawCompoundSlot(slot_name="price", value="799", unit="USD", is_required=True),
                                RawCompoundSlot(slot_name="memory", value="16GB", unit="GB", is_required=True)
                            ],
                            time_context="2024",
                            polarity=True,
                            verifiability=Verifiability.PUBLICLY_VERIFIABLE,
                            verifiability_reason="公开硬件产品规格与官方建议零售价"
                        )
                    ]
                )  # type: ignore
            elif "GAAP" in prompt or "Alphabet" in prompt:
                return DecomposeOutput(
                    claims=[
                        RawDecomposedClaim(
                            statement="Alphabet公布2024年Q3财报GAAP净利润为263.01亿美元，市场非GAAP口径呈现不同分析",
                            subject="Alphabet",
                            predicate="q3_net_income",
                            object_value="263.01亿美元",
                            accounting_basis="GAAP",
                            time_context="Q3 2024",
                            polarity=True,
                            verifiability=Verifiability.PUBLICLY_VERIFIABLE,
                            verifiability_reason="SEC官方10-Q财报定期披露事项"
                        )
                    ]
                )  # type: ignore
            elif "ChatGPT Plus" in prompt:
                return DecomposeOutput(
                    claims=[
                        RawDecomposedClaim(
                            statement="OpenAI ChatGPT Plus 订阅月费维持在20美元",
                            subject="OpenAI ChatGPT Plus",
                            predicate="subscription_pricing",
                            object_value="20美元/月",
                            compound_slots=[
                                RawCompoundSlot(slot_name="price", value="20", unit="USD", is_required=True)
                            ],
                            time_context="2024",
                            polarity=True,
                            verifiability=Verifiability.PUBLICLY_VERIFIABLE,
                            verifiability_reason="官方订阅定价公开透明"
                        )
                    ]
                )  # type: ignore
            elif "Dario Amodei" in prompt or "辞职" in prompt:
                return DecomposeOutput(
                    claims=[
                        RawDecomposedClaim(
                            statement="Anthropic CEO Dario Amodei 于2024年8月辞职并卸任",
                            subject="Dario Amodei",
                            predicate="resignation_departure",
                            time_context="2024-08",
                            polarity=False,
                            verifiability=Verifiability.PUBLICLY_VERIFIABLE,
                            verifiability_reason="知名AI独角兽重大人事变动必有官方或主流媒体报道"
                        )
                    ]
                )  # type: ignore
            elif "宇树" in prompt or "Unitree" in prompt:
                return DecomposeOutput(
                    claims=[
                        RawDecomposedClaim(
                            statement="宇树科技总部位于中国杭州，由创始人兼CEO王兴兴于2016年创立",
                            subject="宇树科技",
                            predicate="corporate_headquarters_and_founding",
                            object_value="中国杭州 王兴兴 2016年",
                            compound_slots=[
                                RawCompoundSlot(slot_name="headquarters", value="杭州", is_required=True),
                                RawCompoundSlot(slot_name="founder", value="王兴兴", is_required=True),
                                RawCompoundSlot(slot_name="founding_year", value="2016", is_required=True)
                            ],
                            time_context="2016-至今",
                            polarity=True,
                            verifiability=Verifiability.PUBLICLY_VERIFIABLE,
                            verifiability_reason="企业官方备案与工商注册公开可查"
                        )
                    ]
                )  # type: ignore
            else:
                return DecomposeOutput(
                    claims=[
                        RawDecomposedClaim(
                            statement=target_name if len(target_name) > 5 else f"{target_name} 于2024年完成近10亿元人民币B2轮融资，美团领投",
                            subject=target_name[:20],
                            predicate="事实陈述",
                            object_value="",
                            time_context="最新",
                            polarity=True,
                            verifiability=Verifiability.PUBLICLY_VERIFIABLE,
                            verifiability_reason="公开事实核验通常有权威媒体或官方渠道披露"
                        )
                    ]
                )  # type: ignore

        if response_model.__name__ == "EvidenceExtractionBatch":
            from app.agents.fast_verifier import EvidenceExtractionBatch, RawExtractedEvidence
            from app.models.verification_models import EvidenceDirectness

            if "RTX 4070" in prompt:
                return EvidenceExtractionBatch(
                    evidences=[
                        RawExtractedEvidence(
                            exact_quote="NVIDIA 官方宣布 GeForce RTX 4070 Ti Super 建议零售价为 $799，搭载 16GB GDDR6X 显存",
                            context="NVIDIA 官方发布会与产品规格表",
                            supports_claim=True,
                            contradicts_claim=False,
                            relation_type="DIRECT_SUPPORT",
                            matched_slots=["price", "memory"],
                            directness=EvidenceDirectness.DIRECT,
                            scope_match=True,
                            evidence_note="官方渠道直接证实价格与显存槽位",
                            origin_credit="NVIDIA 官方公告"
                        ),
                        RawExtractedEvidence(
                            exact_quote="AnandTech 评测：RTX 4070 Ti Super 以 799 美元起售，升级至 16GB 显存",
                            context="权威硬件媒体评测报道",
                            supports_claim=True,
                            contradicts_claim=False,
                            relation_type="DIRECT_SUPPORT",
                            matched_slots=["price", "memory"],
                            directness=EvidenceDirectness.DIRECT,
                            scope_match=True,
                            evidence_note="权威第三方独立印证",
                            origin_credit="AnandTech"
                        )
                    ]
                )  # type: ignore
            elif "GAAP" in prompt or "Alphabet" in prompt:
                return EvidenceExtractionBatch(
                    evidences=[
                        RawExtractedEvidence(
                            exact_quote="Alphabet SEC 10-Q 披露：2024年第三季度 GAAP 净利润录得 263.01 亿美元",
                            context="SEC 官方备案合规财报文件",
                            supports_claim=True,
                            contradicts_claim=False,
                            relation_type="DIRECT_SUPPORT",
                            accounting_standard="GAAP",
                            directness=EvidenceDirectness.DIRECT,
                            scope_match=True,
                            evidence_note="GAAP 会计准则下官方权威确认",
                            origin_credit="SEC 官方财报"
                        ),
                        RawExtractedEvidence(
                            exact_quote="彭博分析师报告：剔除特定股权激励与税费后，部分非GAAP调整后运营指标呈现差异化统计",
                            context="主流财经分析师报告",
                            supports_claim=False,
                            contradicts_claim=False,
                            relation_type="QUALIFIED_CONFLICT",
                            accounting_standard="NON_GAAP",
                            directness=EvidenceDirectness.DIRECT,
                            scope_match=True,
                            evidence_note="合法会计口径分歧",
                            origin_credit="Bloomberg"
                        )
                    ]
                )  # type: ignore
            elif "Dario Amodei" in prompt or "辞职" in prompt:
                return EvidenceExtractionBatch(
                    evidences=[
                        RawExtractedEvidence(
                            exact_quote="Anthropic 官方发言人发布正式声明：关于 CEO Dario Amodei 辞职的传闻纯属谣言，Dario 仍在正常履职",
                            context="Anthropic 官方新闻发言人明确声明",
                            supports_claim=False,
                            contradicts_claim=True,
                            relation_type="AUTHORITATIVE_REFUTE",
                            directness=EvidenceDirectness.DIRECT,
                            scope_match=True,
                            evidence_note="官方权威一手辟谣否认传闻",
                            origin_credit="Anthropic 官方声明"
                        )
                    ]
                )  # type: ignore
            elif "ChatGPT Plus" in prompt:
                return EvidenceExtractionBatch(
                    evidences=[
                        RawExtractedEvidence(
                            exact_quote="OpenAI 官方页面显示 ChatGPT Plus 个人版订阅价格为 20 美元/月",
                            context="OpenAI 官方定价页面",
                            supports_claim=True,
                            contradicts_claim=False,
                            relation_type="DIRECT_SUPPORT",
                            matched_slots=["price"],
                            temporal_evolution="CURRENT",
                            directness=EvidenceDirectness.DIRECT,
                            scope_match=True,
                            evidence_note="官方最新订阅价格确认",
                            origin_credit="OpenAI 官网"
                        )
                    ]
                )  # type: ignore
            elif "宇树" in prompt or "Unitree" in prompt:
                return EvidenceExtractionBatch(
                    evidences=[
                        RawExtractedEvidence(
                            exact_quote="宇树科技官方架构：总部位于中国杭州，由创始人王兴兴于2016年创立",
                            context="宇树科技官方网站公司简介与工商档案",
                            supports_claim=True,
                            contradicts_claim=False,
                            relation_type="DIRECT_SUPPORT",
                            matched_slots=["headquarters", "founder", "founding_year"],
                            directness=EvidenceDirectness.DIRECT,
                            scope_match=True,
                            evidence_note="官方官方架构明确记载总部与创立时间",
                            origin_credit="宇树科技官方"
                        ),
                        RawExtractedEvidence(
                            exact_quote="36氪专访：王兴兴于2016年在杭州创立宇树科技，深耕四足与人形机器人",
                            context="权威科技创投媒体专访报道",
                            supports_claim=True,
                            contradicts_claim=False,
                            relation_type="DIRECT_SUPPORT",
                            matched_slots=["headquarters", "founder", "founding_year"],
                            directness=EvidenceDirectness.DIRECT,
                            scope_match=True,
                            evidence_note="主流权威媒体独立印证",
                            origin_credit="36氪"
                        )
                    ]
                )  # type: ignore
            else:
                return EvidenceExtractionBatch(
                    evidences=[
                        RawExtractedEvidence(
                            exact_quote=f"{target_name} 官方正式宣布完成近10亿元人民币B2轮融资，美团领投",
                            context="官方公告与财经快讯均有详细报道",
                            supports_claim=True,
                            contradicts_claim=False,
                            relation_type="DIRECT_SUPPORT",
                            directness=EvidenceDirectness.DIRECT,
                            scope_match=True,
                            evidence_note="官方渠道直接确认",
                            origin_credit="公司官方公告"
                        ),
                        RawExtractedEvidence(
                            exact_quote=f"36氪科技创投报道：{target_name} 完成近10亿元B2轮融资，投资方包括美团与金石投资",
                            context="主流财经媒体独立跟进报道",
                            supports_claim=True,
                            contradicts_claim=False,
                            relation_type="DIRECT_SUPPORT",
                            directness=EvidenceDirectness.DIRECT,
                            scope_match=True,
                            evidence_note="主流财经媒体独立印证",
                            origin_credit="36氪"
                        )
                    ]
                )  # type: ignore

        if response_model.__name__ == "VerdictExplanationOutput":
            from app.agents.fast_verifier import VerdictExplanationOutput
            return VerdictExplanationOutput(
                why_reasons=[
                    "✓ 找到 2 个相互独立的权威信息源证实该融资事件",
                    "✓ 获得企业官方公告与主流财经创投直接确认",
                    "ℹ️ 未发现主要投资方或监管层面的相悖反驳"
                ],
                evidence_gaps=[
                    "尚未查验对应工商登记实缴资本变更记录"
                ],
                next_step_advice="如需进一步核实细节，可查阅全国企业信用信息公示系统或国家企业信用信息报告。"
            )  # type: ignore

        # 4. Report Synthesis
        if response_model == StructuredSynthesisOutput:
            if is_unitree:
                md = f"""# 宇树科技 (Unitree Robotics) 深度事实调查与前沿情报研报 (2025-2026)

## 1. 执行摘要与核心结论 (Executive Summary)
杭州宇树科技有限公司（Unitree Robotics）作为全球具身智能与足式机器人头部领军企业，在 2024-2026 年实现了四足机器人全球市占领先与通用人形机器人量产突破。公司完成近 10 亿元人民币 B2 轮融资 [1]，由创始人兼 CEO 王兴兴掌舵 [2]，推出 9.9 万元起售的普及型全尺寸人形机器人 Unitree G1 [3]，但在复杂灵巧操作与具身大模型算法泛化上仍面临行业共性演进挑战 [4]。

## 2. 创始人与核心组织架构 (Leadership & Governance)
- **创始人基因**：宇树科技由王兴兴于 2016 年创立 [2]。王兴兴在上海大学读研期间自研 XDog 四足机器人，开创了外转子电机驱动四足机器人的技术先河，技术直觉敏锐且对硬件成本控制具备极高执念。
- **总部与团队**：公司总部位于杭州滨江区，研发人员占比超过 50%，核心覆盖机械结构、电机电控、运动控制算法及具身感知决策。

## 3. 产品矩阵与技术路线 (Products & Technology)
- **四足机器人矩阵**：涵盖工业级防爆巡检四足机器人（Unitree B2）与消费级/科教四足机器人（Unitree Go2）[2]。
- **人形机器人突破**：发布全尺寸人形机器人 Unitree H1（曾创下全尺寸人形机器人奔跑速度世界纪录）与全新量产型人形机器人 Unitree G1，官方定价 9.9 万元人民币起 [3]。
- **核心零部件自研**：自研高扭矩密度关节电机、减速器与自制动力学运控算法，具备全产业链垂直整合能力。

## 4. 融资历程与资本版图 (Funding & Capital)
- **B2轮近10亿元**：美团、金石投资、深创投联合领投，老股东红杉中国跟投 [1]。
- **战投资金用途**：主要投向人形机器人核心零部件供应链量产建设、具身世界模型训练与全球出海销售网络布局。

## 5. 潜在风险与行业争议 (Risks & Controversies)
- **灵巧手与高阶操作短板**：当前双足行走与奔跑跳跃表现优异，但在非结构化复杂家庭/工业场景中的精细双手抓取依然受限 [4]。
- **价格战与毛利权衡**：9.9 万元定价对行业供应链形成颠覆性冲击，但对量产良品率与前期研发摊销提出了极高要求 [4]。

## 6. 引用信源清单 (Verified Citations)
- **[1]** [36氪 科技创投](https://www.36kr.com) - *宇树科技完成近10亿元B2轮融资，美团与深创投联合领投* (🟢 基本确认)
- **[2]** [宇树科技官方架构](https://www.unitree.com) - *创始人王兴兴与产品技术路线图* (🟢 已确认)
- **[3]** [官方量产发布会](https://www.unitree.com) - *人形机器人G1定价9.9万元起* (🟢 已确认)
- **[4]** [行业技术深度评测](https://www.zhihu.com) - *人形机器人灵巧手与算法泛化短板分析* (⚪ 观点推论)
"""
            else:
                md = f"""# {target_name} 深度事实调查与前沿情报研报 (2025-2026)

## 1. 执行摘要与核心结论 (Executive Summary)
本报告针对「{target_name}」完成了多源定向调查、事实提取与交叉验证。综合官方备案、权威新闻报道及行业社区讨论，{target_name} 在 2024-2026 年间实现了核心业务跨越式增长 [1]，全球化合规稳健运营 [2]，并在产品交付与生态构建中持续迭代优化 [3]。

## 2. 核心事实与核验证据 (Verified Facts)
- **业务规模与增长**：权威行业调研显示其年营收规模与商业化落地稳步推进 [1]。
- **组织治理与合规**：官方监管披露证实其保持合规稳健运营，在全球设立多处运营节点 [2]。
- **社区与用户反馈**：社区整体评价良好，同时在高端交付周期上存在部分改进建议 [3]。

## 3. 引用信源清单 (Verified Citations)
- **[1]** [Reuters 行业综合调研](https://www.reuters.com) - *核心业务跨越式增长与商业化落地* (🟢 基本确认)
- **[2]** [SEC 官方合规档案](https://www.sec.gov) - *组织治理与稳健运营* (🟢 已确认)
- **[3]** [行业社区评测与反馈](https://www.reddit.com) - *市场反馈与交付建议* (⚪ 观点推论)
"""

            return StructuredSynthesisOutput(
                title=f"{target_name} 深度事实调查与前沿情报研报 (2025-2026)",
                executive_summary=f"本报告针对目标「{target_name}」完成了多源全网侦察、事实提取与交叉验证。汇总多维度权威信源，提取并核验原子主张，全方位透视其团队、产品、商业模式与潜在风险。",
                markdown_content=md,
                credibility_breakdown={"average_credibility": 0.88}
            )  # type: ignore

        # Generic default via schema default/fields
        schema = response_model.model_json_schema()
        dummy_data = {}
        for prop, details in schema.get("properties", {}).items():
            prop_type = details.get("type")
            if prop_type == "string":
                dummy_data[prop] = f"Mock {prop}"
            elif prop_type == "integer":
                dummy_data[prop] = 1
            elif prop_type == "number":
                dummy_data[prop] = 0.85
            elif prop_type == "array":
                dummy_data[prop] = []
            elif prop_type == "boolean":
                dummy_data[prop] = True
            elif prop_type == "object":
                dummy_data[prop] = {}
        return response_model.model_validate(dummy_data)

    async def get_embedding(self, text: str) -> list[float]:
        """Generate deterministic pseudo-embedding based on text hash"""
        h = hashlib.sha256(text.encode("utf-8")).digest()
        # Expand 32 bytes to 768 floats between -1.0 and 1.0
        vec = []
        for i in range(768):
            b = h[i % len(h)]
            vec.append((float(b) / 128.0) - 1.0)
        return vec
