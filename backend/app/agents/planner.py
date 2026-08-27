import logging
from typing import Optional
from app.models.schemas import ResearchPlan, TargetType, SubTask
from app.providers.llm.base import LLMProvider
from app.providers.llm import get_llm_provider

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are an elite Investigative Research Planner & Intelligence Architect.
Your task is to analyze an investigation target and produce a rigorous, multi-dimensional Research Plan customized to the specific investigation category.

CATEGORY-SPECIFIC INVESTIGATION METHODOLOGIES:
1. [COMPANY] (企业全景背调):
   - Dimension 1: 创始人履历、技术基因与核心治理结构 (Founders, Background & Governance)
   - Dimension 2: 融资历程、真实估值、资方背书与财务营收 (Funding, Valuation & Financials)
   - Dimension 3: 产品矩阵、核心技术护城河与供应链自研 (Products & Supply Chain Moat)
   - Dimension 4: 潜在风险、未决诉讼、监管处罚与行业短板 (Risks, Lawsuits, Regulatory & Shortcomings)

2. [PRODUCT] (真实产品评测与口碑调研):
   - Dimension 1: 核心技术规格、参数对比与官方宣传点 (Specs & Marketing Claims)
   - Dimension 2: 真实用户实测体验、故障率与缺陷反馈 (User Experience, Failure Rates & Defects)
   - Dimension 3: 与竞品横向对比与真实性价比 (Benchmarking & Competitor Comparison)
   - Dimension 4: 价格体系、渠道毛利与售后服务质量 (Pricing, Margins & After-sales)

3. [INVESTMENT] (投资尽调与商业真实性排查):
   - Dimension 1: 商业模式闭环与造血盈利能力 (Unit Economics & Real Revenue)
   - Dimension 2: 真实资产规模、历史资方资质与估值合理性 (Assets, Cap Table & Valuation Sanity)
   - Dimension 3: 关联交易、虚假宣传、庞氏或非法集资风险 (Fraud, Ponzi Risks & Conflicts of Interest)
   - Dimension 4: 政策合规、退出通道与法律纠纷 (Regulatory Compliance & Legal Exposure)

4. [CLAIM] (事实核验与辟谣追踪):
   - Dimension 1: 原始出处溯源、首发账号与传播时间线 (Origin, First Publication & Timeline)
   - Dimension 2: 权威官方通报、当事方正式声明与官方辟谣 (Official Statements & Corroborations)
   - Dimension 3: 传播链分析、舆论反转与关键反证证据 (Evidence Chain, Rebuttals & Counter-evidence)
   - Dimension 4: 事实真伪判定依据与核心未解疑点 (Definitive Verdict & Remaining Gaps)

5. [TECHNOLOGY] (前沿技术真实性与成熟度评估):
   - Dimension 1: 底层科学原理、学术论文与核心专利分布 (Scientific Principles, Papers & Patents)
   - Dimension 2: 第三方权威 Benchmark 实测与复现情况 (Independent Benchmarks & Reproducibility)
   - Dimension 3: 行业专家评价与与主流技术路线差异 (Expert Consensus vs Mainstream Approaches)
   - Dimension 4: 宣传夸大、工程落地阻碍与商业化天花板 (Hype vs Reality, Engineering Barriers)

Provide 2 targeted, highly discerning web search queries per sub-task. Include specific search keywords (e.g., "诉讼", "评测", "真假", "辟谣", "财报", "投资人") to avoid generic low-quality results.
"""

class PlannerAgent:
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm = llm_provider or get_llm_provider(tier="fast")

    async def plan(self, target_query: str, target_type_hint: Optional[TargetType] = None) -> ResearchPlan:
        user_prompt = f"Investigation Target: \"{target_query}\"\n"
        if target_type_hint:
            user_prompt += f"Suggested Target Category: {target_type_hint.value}\n"
        user_prompt += "\nDecompose this investigation into a structured Research Plan according to the schema."

        try:
            plan = await self.llm.generate_structured(
                prompt=user_prompt,
                response_model=ResearchPlan,
                system_prompt=PLANNER_SYSTEM_PROMPT,
                temperature=0.1
            )
            return plan
        except Exception as e:
            logger.warning(f"LLM planning failed: {e}. Generating fallback plan.")
            return ResearchPlan(
                target_type=target_type_hint or TargetType.GENERAL,
                target_name=target_query,
                key_hypotheses=[
                    f"Understanding key operations and current standing of {target_query}.",
                    f"Identifying controversies, lawsuits, or disputed claims around {target_query}."
                ],
                sub_tasks=[
                    SubTask(
                        id="task-1",
                        dimension="Background & Overview",
                        question=f"What is the official background and core structure of {target_query}?",
                        search_queries=[f"{target_query} background overview", f"{target_query} official founders history"],
                        rationale="Establish foundational facts."
                    ),
                    SubTask(
                        id="task-2",
                        dimension="Business & Metrics",
                        question=f"What are the verified financials, products, or metrics of {target_query}?",
                        search_queries=[f"{target_query} revenue valuation metrics", f"{target_query} product evaluation"],
                        rationale="Verify performance claims."
                    ),
                    SubTask(
                        id="task-3",
                        dimension="Risks & Controversies",
                        question=f"What controversies, criticisms, or regulatory risks exist for {target_query}?",
                        search_queries=[f"{target_query} controversy lawsuit scandal", f"{target_query} investigation complaints"],
                        rationale="Uncover hidden risks and conflicting viewpoints."
                    ),
                ]
            )
