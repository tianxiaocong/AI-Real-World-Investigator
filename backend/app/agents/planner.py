import logging
from typing import Optional
from app.models.schemas import ResearchPlan, TargetType, SubTask
from app.providers.llm.base import LLMProvider
from app.providers.llm import get_llm_provider

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are an elite Investigative Research Planner & Intelligence Architect.
Your task is to analyze an investigation target and produce a rigorous, multi-dimensional Research Plan.

Your plan must:
1. Classify the target type accurately (COMPANY, PERSON, PRODUCT, TECHNOLOGY, BUSINESS_MODEL, CLAIM, JOB_OPPORTUNITY, INVESTMENT, GENERAL).
2. Formulate 2-3 core hypotheses to be tested.
3. Break the investigation down into 3-5 distinct sub-task dimensions:
   - Background, Governance & Leadership
   - Core Operations, Products, Commercial Metrics & Financials
   - Controversies, Lawsuits, Regulatory Actions & Hidden Risks
   - Market Competitors & Verified Technological Differentiators
4. For each sub-task, provide 2 targeted web search queries designed to find independent, high-authority sources (including official filings, news, and critical discussions).
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
