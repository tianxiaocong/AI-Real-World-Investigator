import json
import logging
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.models.schemas import ReportResponse, ClaimType, VerificationStatus
from app.providers.llm.base import LLMProvider
from app.providers.llm import get_llm_provider

logger = logging.getLogger(__name__)

class StructuredSynthesisOutput(BaseModel):
    title: str = Field(..., description="Report Title (e.g. 'OpenAI 深度调查与事实核验报告')")
    executive_summary: str = Field(..., description="High-level executive summary of key verified findings.")
    markdown_content: str = Field(..., description="Full structured investigative report in GitHub Markdown with [1], [2] citation markers.")
    credibility_breakdown: Dict[str, Any] = Field(default_factory=dict, description="Distribution of source types and credibility index.")

SYNTHESIZER_SYSTEM_PROMPT = """You are a Principal Intelligence Dossier Synthesizer and Investigative Journalist.
Your task is to synthesize verified claims and sources into a comprehensive, highly rigorous investigation report.

CRITICAL CITATION RULES:
1. Every significant assertion, metric, date, or controversy MUST cite a specific Citation Index like [1], [2], [3] that corresponds to the given Claims and Sources list.
2. DO NOT make ungrounded generalizations. If something is an OPINION or UNVERIFIED, clearly label it as such in the text.
3. Highlight any CONFLICTING claims in a dedicated "Controversies & Disputed Facts (争议与矛盾事实)" section.
4. Structure the report professionally with the following 15 standard sections:
   1. 执行摘要与核心结论 (Executive Summary & Key Findings)
   2. 组织架构与管理层背景 (Governance & Leadership)
   3. 核心产品与业务版图 (Products & Operations)
   4. 商业模式与客户群体 (Business Model)
   5. 融资历史与主要投资方 (Funding & Investors)
   6. 财务状况与营收估算 (Financials & Revenue)
   7. 技术路线与真实评测对比 (Technology & Benchmarks)
   8. 招聘规模与组织变动 (Team & Hiring)
   9. 行业竞争格局与护城河 (Competition & Moats)
   10. 核心竞争优势 (Core Strengths)
   11. 潜在风险清单 (Identified Risks)
   12. 争议与矛盾事实 (Disputed Claims & Conflicts)
   13. 未经证实的传闻 (Unverified Rumors)
   14. 调查结论与行动建议 (Final Verdict & Recommendations)
   15. 引用信源清单 (References)
"""

class SynthesizerAgent:
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm = llm_provider or get_llm_provider(tier="reasoning")

    async def synthesize_report(
        self,
        target_name: str,
        claims: List[Dict[str, Any]],
        sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compiles verified claims and sources into a structured investigation report
        and builds the citation mapping table.
        """
        # Build mapping index: Index 1..N mapped to claim & its primary source
        citation_map = {}
        claims_context_list = []

        for idx, c in enumerate(claims, start=1):
            cid = str(idx)
            primary_source = c.get("sources", [{}])[0] if c.get("sources") else {}
            
            citation_map[cid] = {
                "citation_index": idx,
                "claim_id": c.get("id"),
                "statement": c.get("statement"),
                "claim_type": c.get("claim_type", ClaimType.FACT).value if hasattr(c.get("claim_type"), "value") else str(c.get("claim_type")),
                "verification_status": c.get("verification_status", VerificationStatus.UNVERIFIED).value if hasattr(c.get("verification_status"), "value") else str(c.get("verification_status")),
                "confidence": c.get("confidence", "MEDIUM"),
                "source_url": primary_source.get("url", ""),
                "source_domain": primary_source.get("domain", ""),
                "source_title": primary_source.get("title", ""),
                "source_credibility": primary_source.get("credibility_score", 0.5),
                "quote": primary_source.get("exact_quote", ""),
                "context_prefix": primary_source.get("context_prefix", ""),
                "context_suffix": primary_source.get("context_suffix", "")
            }

            claims_context_list.append(
                f"[{idx}] Statement: \"{c.get('statement')}\"\n"
                f"    Type: {c.get('claim_type')} | Status: {c.get('verification_status')} | Confidence: {c.get('confidence')}\n"
                f"    Source: {primary_source.get('domain')} ({primary_source.get('url')})\n"
                f"    Quote: \"{primary_source.get('exact_quote')}\""
            )

        claims_context = "\n\n".join(claims_context_list)
        sources_summary = "\n".join([f"- {s.get('domain')} ({s.get('source_type')}): {s.get('title')} [{s.get('url')}]" for s in sources])

        prompt = (
            f"Investigation Target: \"{target_name}\"\n\n"
            f"=== RETRIEVED SOURCES ({len(sources)}) ===\n{sources_summary}\n\n"
            f"=== VERIFIED CLAIMS & CITATION INDICES ({len(claims)}) ===\n{claims_context}\n\n"
            f"Synthesize the complete 15-section investigative dossier using citation markers like [1], [2] referencing the claims above."
        )

        try:
            output = await self.llm.generate_structured(
                prompt=prompt,
                response_model=StructuredSynthesisOutput,
                system_prompt=SYNTHESIZER_SYSTEM_PROMPT,
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
            return self._generate_fallback_report(target_name, claims, sources, citation_map)

    def _lint_and_append_sources(self, markdown: str, citation_map: Dict[str, Any]) -> str:
        """Appends interactive source index table to report if not already complete"""
        if "## 15. 引用信源清单" not in markdown and "## 15. Sources" not in markdown:
            ref_section = "\n\n## 15. 引用信源清单 (Verified Citations)\n\n"
            for k, v in citation_map.items():
                ref_section += f"- **[{k}]** [{v.get('source_title') or v.get('source_domain')}]({v.get('source_url')}) - *{v.get('statement')}* (`{v.get('claim_type')}`, 状态: `{v.get('verification_status')}`)\n"
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
            types_count[st] = types_count.get(st, 0) + 1
        
        claims_stat = {
            "total": len(claims),
            "fact": sum(1 for c in claims if c.get("claim_type") in ("FACT", ClaimType.FACT)),
            "conflicting": sum(1 for c in claims if c.get("claim_type") in ("CONFLICTING", ClaimType.CONFLICTING)),
            "opinion": sum(1 for c in claims if c.get("claim_type") in ("OPINION", ClaimType.OPINION)),
            "unverified": sum(1 for c in claims if c.get("claim_type") in ("UNVERIFIED", ClaimType.UNVERIFIED)),
            "inference": sum(1 for c in claims if c.get("claim_type") in ("INFERENCE", ClaimType.INFERENCE)),
        }
        
        avg_cred = (sum(s.get("credibility_score", 0.5) for s in sources) / len(sources)) if sources else 0.5
        return {
            "average_credibility": round(avg_cred, 2),
            "sources_by_type": types_count,
            "claims_distribution": claims_stat
        }

    def _generate_fallback_report(
        self,
        target_name: str,
        claims: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
        citation_map: Dict[str, Any]
    ) -> Dict[str, Any]:
        title = f"{target_name} 事实调查与情报核验报告"
        exec_summary = f"本报告针对目标「{target_name}」完成了多源侦察、事实提取与交叉验证。共汇总 {len(sources)} 个权威信源，提取并核验 {len(claims)} 条原子主张。"
        
        md_lines = [
            f"# {title}",
            "",
            "## 1. 执行摘要与核心结论 (Executive Summary)",
            exec_summary,
            "",
            "## 2. 核心事实与核验证据 (Verified Facts)",
        ]
        for idx, c in enumerate(claims, start=1):
            md_lines.append(f"- **[{idx}]** {c.get('statement')} *(类型: `{c.get('claim_type')}`, 核验: `{c.get('verification_status')}`)*")
            
        md_lines.append("")
        md_lines.append("## 15. 引用信源清单 (Verified Citations)")
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
