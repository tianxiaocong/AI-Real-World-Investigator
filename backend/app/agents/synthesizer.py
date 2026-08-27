import json
import logging
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.models.schemas import ReportResponse, ClaimType, VerificationStatus, TargetType
from app.providers.llm.base import LLMProvider
from app.providers.llm import get_llm_provider

logger = logging.getLogger(__name__)

class StructuredSynthesisOutput(BaseModel):
    title: str = Field(..., description="Report Title (e.g. 'OpenAI 深度调查与事实核验报告')")
    executive_summary: str = Field(..., description="High-level executive summary answering 'What is true? What is disputed? What is unverified?'.")
    markdown_content: str = Field(..., description="Full structured investigative report in GitHub Markdown with [1], [2] citation markers.")
    credibility_breakdown: Dict[str, Any] = Field(default_factory=dict, description="Distribution of source types and verification status.")

def get_synthesizer_prompt_for_target_type(target_type: TargetType) -> str:
    if target_type in (TargetType.CLAIM, TargetType.INVESTMENT):
        return """You are a Principal Fact-Checking Arbiter and Forensic Intelligence Investigator.
Your task is to synthesize verified claims and sources into a rigorous, objective Fact-Checking & Due-Diligence Investigation Report.

CRITICAL CITATION RULES:
1. Every significant assertion, metric, date, or controversy MUST cite a specific Citation Index like [1], [2], [3].
2. Answer the key investigative questions upfront: What is confirmed? What is disputed? What lacks evidence?
3. Format the report cleanly using the following focused sections:
   ## 1. 调查结论与真伪裁决 (Fact-Check Verdict & Executive Summary)
   ## 2. 传言背景与原始出处溯源 (Origin & Propagation)
   ## 3. 支持性证据链核验 (Supporting Evidence & Corroboration)
   ## 4. 关键矛盾与反证分析 (Counter-Evidence & Contradictions)
   ## 5. 官方主体公开通报与合规声明 (Official Disclosures)
   ## 6. 仲裁研判与定论依据 (Arbiter Reasoning & Takeaways)
   ## 7. 引用信源清单 (Verified Citations)
"""
    elif target_type in (TargetType.PRODUCT, TargetType.TECHNOLOGY):
        return """You are a Principal Technology Intelligence Analyst and Technical Due-Diligence Investigator.
Your task is to synthesize verified claims and sources into a rigorous Product & Technology Fact-Checking Report.

CRITICAL CITATION RULES:
1. Every significant spec, benchmark, user complaint, or commercial claim MUST cite a specific Citation Index like [1], [2], [3].
2. Clearly distinguish between marketing claims vs independent verified third-party benchmarks.
3. Format the report cleanly using the following focused sections:
   ## 1. 核心结论与综合评级 (Executive Summary & Assessment)
   ## 2. 硬件规格与官方宣称指标 (Specs & Official Claims)
   ## 3. 第三方独立评测与基准实测 (Verified Benchmarks & Independent Tests)
   ## 4. 已知短板、缺陷与用户争议 (Known Flaws & User Controversies)
   ## 5. 行业竞品横评与壁垒 (Competitive Comparison & Real Moats)
   ## 6. 调查结论与选型决策建议 (Final Takeaways & Guidance)
   ## 7. 引用信源清单 (Verified Citations)
"""
    else:
        return """You are a Principal Intelligence Dossier Synthesizer and Investigative Journalist.
Your task is to synthesize verified claims and sources into a comprehensive, highly rigorous Enterprise & Entity Investigation Report.

CRITICAL CITATION RULES:
1. Every significant assertion, metric, date, or controversy MUST cite a specific Citation Index like [1], [2], [3].
2. Answer the key investigative questions clearly: What is verified? What is disputed? What remains unverified?
3. Format the report cleanly using the following focused sections:
   ## 1. 执行摘要与核心结论 (Executive Summary & Key Findings)
   ## 2. 组织架构与核心治理背景 (Governance & Leadership)
   ## 3. 核心产品、技术路线与业务版图 (Products & Operations)
   ## 4. 商业模式、融资历程与财务估算 (Business Model, Funding & Financials)
   ## 5. 行业竞争格局与核心壁垒 (Competition & Core Moats)
   ## 6. 潜在风险与争议矛盾核验 (Identified Risks & Disputed Claims)
   ## 7. 调查最终裁决与行动建议 (Final Investigation Verdict)
   ## 8. 引用信源清单 (Verified Citations)
"""

class SynthesizerAgent:
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm = llm_provider or get_llm_provider(tier="reasoning")

    async def synthesize_report(
        self,
        target_name: str,
        claims: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
        target_type: TargetType = TargetType.COMPANY
    ) -> Dict[str, Any]:
        """
        Compiles verified claims and sources into a dynamic structured investigation report
        and builds the citation mapping table.
        """
        citation_map = {}
        claims_context_list = []

        for idx, c in enumerate(claims, start=1):
            cid = str(idx)
            primary_source = c.get("sources", [{}])[0] if c.get("sources") else {}
            
            c_type = c.get("claim_type", ClaimType.FACT_STATEMENT)
            c_type_str = c_type.value if hasattr(c_type, "value") else str(c_type)
            v_status = c.get("verification_status", VerificationStatus.UNVERIFIED)
            v_status_str = v_status.value if hasattr(v_status, "value") else str(v_status)

            all_supporting_domains = [s.get("domain") for s in c.get("sources", []) if s.get("domain")]

            citation_map[cid] = {
                "citation_index": idx,
                "claim_id": c.get("id"),
                "statement": c.get("statement"),
                "claim_type": c_type_str,
                "verification_status": v_status_str,
                "verdict_summary": c.get("verdict_summary") or v_status_str,
                "verdict_reasons": c.get("verdict_reasons", []),
                "independent_sources_count": c.get("independent_sources_count", 1),
                "source_tiers_summary": c.get("source_tiers_summary", {}),
                "confidence": c.get("confidence", "MEDIUM"),
                "source_url": primary_source.get("url", ""),
                "source_domain": primary_source.get("domain", ""),
                "source_title": primary_source.get("title", ""),
                "source_type": primary_source.get("source_type", "OTHER"),
                "source_credibility": primary_source.get("credibility_score", 0.5),
                "quote": primary_source.get("exact_quote", ""),
                "context_prefix": primary_source.get("context_prefix", ""),
                "context_suffix": primary_source.get("context_suffix", ""),
                "all_sources": c.get("sources", []),
                "contradictions": c.get("contradictions", [])
            }

            claims_context_list.append(
                f"[{idx}] Statement: \"{c.get('statement')}\"\n"
                f"    Verdict: {c.get('verdict_summary', v_status_str)} | Type: {c_type_str} | Independent Sources: {len(set(all_supporting_domains))}\n"
                f"    Primary Source: {primary_source.get('domain')} ({primary_source.get('url')})\n"
                f"    Quote: \"{primary_source.get('exact_quote')}\""
            )

        claims_context = "\n\n".join(claims_context_list)
        sources_summary = "\n".join([f"- {s.get('domain')} ({s.get('source_type')}): {s.get('title')} [{s.get('url')}]" for s in sources])

        sys_prompt = get_synthesizer_prompt_for_target_type(target_type)
        prompt = (
            f"Investigation Target: \"{target_name}\" (Target Type: {target_type.value if hasattr(target_type, 'value') else target_type})\n\n"
            f"=== RETRIEVED SOURCES ({len(sources)}) ===\n{sources_summary}\n\n"
            f"=== VERIFIED CLAIMS & CITATION INDICES ({len(claims)}) ===\n{claims_context}\n\n"
            f"Synthesize the investigative dossier using citation markers like [1], [2] referencing the claims above. Ensure every core metric or finding cites its citation index."
        )

        try:
            output = await self.llm.generate_structured(
                prompt=prompt,
                response_model=StructuredSynthesisOutput,
                system_prompt=sys_prompt,
                temperature=0.2
            )
            
            # Post-processing: run Citation Linter
            markdown = self._lint_and_append_sources(output.markdown_content, citation_map)
            
            return {
                "title": output.title,
                "executive_summary": output.executive_summary,
                "markdown_content": markdown,
                "structured_sections": self._parse_markdown_sections(markdown),
                "citation_map": citation_map,
                "credibility_breakdown": self._calculate_credibility_breakdown(sources, claims)
            }
        except Exception as e:
            logger.warning(f"Synthesis failed: {e}. Using fallback generator.")
            return self._generate_fallback_report(target_name, claims, sources, citation_map, target_type)

    def _lint_and_append_sources(self, markdown: str, citation_map: Dict[str, Any]) -> str:
        """Appends interactive source index table to report if not already complete"""
        if "引用信源清单" not in markdown and "References" not in markdown:
            ref_section = "\n\n## 引用信源清单 (Verified Citations)\n\n"
            for k, v in citation_map.items():
                ref_section += f"- **[{k}]** [{v.get('source_title') or v.get('source_domain')}]({v.get('source_url')}) - *{v.get('statement')}* ({v.get('verdict_summary') or v.get('verification_status')})\n"
            markdown += ref_section
        return markdown

    def _parse_markdown_sections(self, markdown: str) -> List[Dict[str, Any]]:
        """Parses H2 markdown headings into structured navigation sections"""
        sections = []
        pattern = r"##\s+(.+?)\n([\s\S]*?)(?=(##\s+|$))"
        matches = re.findall(pattern, markdown)
        for idx, match in enumerate(matches):
            title = match[0].strip()
            content = match[1].strip()
            sections.append({
                "section_id": f"sec-{idx+1}",
                "title": title,
                "content_markdown": content
            })
        return sections

    def _calculate_credibility_breakdown(self, sources: List[Dict[str, Any]], claims: List[Dict[str, Any]]) -> Dict[str, Any]:
        types_count = {}
        for s in sources:
            st = s.get("source_type", "OTHER")
            st_str = st.value if hasattr(st, "value") else str(st)
            types_count[st_str] = types_count.get(st_str, 0) + 1
        
        claims_stat = {
            "total": len(claims),
            "confirmed": sum(1 for c in claims if c.get("verification_status") in ("CONFIRMED", VerificationStatus.CONFIRMED)),
            "probable": sum(1 for c in claims if c.get("verification_status") in ("PROBABLE", VerificationStatus.PROBABLE)),
            "single_source": sum(1 for c in claims if c.get("verification_status") in ("SINGLE_SOURCE", VerificationStatus.SINGLE_SOURCE)),
            "disputed": sum(1 for c in claims if c.get("verification_status") in ("DISPUTED", VerificationStatus.DISPUTED) or c.get("claim_type") in ("DISPUTED", ClaimType.DISPUTED)),
            "unverified": sum(1 for c in claims if c.get("verification_status") in ("UNVERIFIED", VerificationStatus.UNVERIFIED)),
            "opinion_only": sum(1 for c in claims if c.get("verification_status") in ("OPINION_ONLY", VerificationStatus.OPINION_ONLY)),
        }
        
        avg_cred = round(sum(s.get("credibility_score", 0.0) for s in sources) / len(sources), 2) if sources else None
        return {
            "average_credibility": avg_cred,
            "sources_by_type": types_count,
            "claims_distribution": claims_stat
        }

    def _generate_fallback_report(
        self,
        target_name: str,
        claims: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
        citation_map: Dict[str, Any],
        target_type: TargetType = TargetType.COMPANY
    ) -> Dict[str, Any]:
        title = f"{target_name} 事实调查与情报核验报告"
        if not sources:
            exec_summary = f"本次调查针对目标「{target_name}」发起了针对性多源定向检索，但未能从公开互联网检索到足够且具备权威性的事实信源。根据 Evidence-First 零造假原则，系统未生成推测性结论，所有规划假设当前标记为未证实状态。"
        else:
            exec_summary = f"本报告针对目标「{target_name}」完成了多源定向调查、事实提取与交叉验证。共汇总 {len(sources)} 个权威信源，提取并核验 {len(claims)} 条原子主张。"
        
        md_lines = [
            f"# {title}",
            "",
            "## 1. 调查结论与执行摘要 (Executive Summary)",
            exec_summary,
            "",
            "## 2. 核心事实与核验证据 (Verified Facts)",
        ]
        for idx, c in enumerate(claims, start=1):
            verdict_text = c.get("verdict_summary") or c.get("verification_status", "未证实")
            md_lines.append(f"- **[{idx}]** {c.get('statement')} *({verdict_text})*")
            
        md_lines.append("")
        md_lines.append("## 3. 引用信源清单 (Verified Citations)")
        for k, v in citation_map.items():
            md_lines.append(f"- **[{k}]** [{v.get('source_title') or v.get('source_domain')}]({v.get('source_url')}) - *{v.get('statement')}*")

        full_md = "\n".join(md_lines)
        return {
            "title": title,
            "executive_summary": exec_summary,
            "markdown_content": full_md,
            "structured_sections": self._parse_markdown_sections(full_md),
            "citation_map": citation_map,
            "credibility_breakdown": self._calculate_credibility_breakdown(sources, claims)
        }
