import logging
from typing import List, Optional, Any
from pydantic import BaseModel, Field
from app.models.schemas import ClaimType, ConfidenceLevel, SourceType
from app.providers.llm.base import LLMProvider
from app.providers.llm import get_llm_provider
from app.scraper.extractor import WebScraper
from app.core.security import wrap_untrusted_content

logger = logging.getLogger(__name__)

class ExtractedProvenance(BaseModel):
    relation: str = Field(..., description="REPUBLISHES, CITES, or NONE.")
    target_source_id: Optional[str] = Field(None, description="The origin_source_id if relation is not NONE.")
    evidence_quote: Optional[str] = Field(None, description="The verbatim quote proving the relation.")

class RawExtractedClaim(BaseModel):
    statement: str = Field(..., description="An atomic factual, inferential, opinionated, or rumor assertion in concise language.")
    exact_quote: str = Field(..., description="The verbatim, word-for-word quote from the text that directly supports this claim.")
    claim_type: ClaimType = Field(..., description="FACT_STATEMENT (objective verifiable facts), OPINION (subjective viewpoints/ratings), INFERENCE (reasoned conclusions), RUMOR (unverified chatter/leaks), DISPUTED (openly disputed assertions).")
    confidence: ConfidenceLevel = Field(..., description="HIGH, MEDIUM, or LOW confidence in this assertion extraction.")
    reasoning: Optional[str] = Field(None, description="Brief explanation of why this claim nature and confidence was assigned.")
    provenance: Optional[ExtractedProvenance] = Field(None, description="If this text explicitly republished or cites another URL as the ultimate origin of this statement.")

class ClaimExtractionBatch(BaseModel):
    claims: List[RawExtractedClaim] = Field(default_factory=list)

CLAIM_EXTRACTOR_SYSTEM_PROMPT = """You are an expert Forensic Intelligence Analyst and Claim Extractor.
Your job is to read raw text (which may be HTML or text) from a web source and extract key atomic claims, focusing heavily on exactly citing the source.

RULES:
1. "exact_quote" MUST BE A VERBATIM, EXACT character-for-character substring found in the source text. Never paraphrase or alter the quote.
2. An atomic claim is a single testable statement.
3. Strictly classify statement nature (claim_type).
4. Extract PROVENANCE. If the text explicitly states it is republishing from, or citing another specific URL or source name as the ultimate origin of this statement, fill out the `provenance` object.
   - Set relation to "REPUBLISHES" if it is a direct syndication or republication.
   - Set relation to "CITES" if it attributes the claim to another specific article or report.
   - Set relation to "NONE" if it is original reporting or no explicit citation is found.
5. Set confidence based on clarity and specificity of the evidence.
"""

class ClaimExtractorAgent:
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm = llm_provider or get_llm_provider(tier="fast")

    async def extract_claims_from_source(
        self,
        clean_text: str,
        source_url: str,
        source_type: Any,
        target_name: str
    ) -> List[dict]:
        """
        Extracts validated atomic claims from text, ensuring character-level anchor matching.
        """
        truncated_text = clean_text[:8000]
        wrapped = wrap_untrusted_content(truncated_text)
        st_val = source_type.value if hasattr(source_type, "value") else str(source_type)

        prompt = (
            f"Investigation Target: {target_name}\n"
            f"Source URL: {source_url}\n"
            f"Source Type: {st_val}\n\n"
            f"Extract the most significant atomic claims related to {target_name} from the content below.\n\n"
            f"{wrapped}"
        )

        try:
            batch = await self.llm.generate_structured(
                prompt=prompt,
                response_model=ClaimExtractionBatch,
                system_prompt=CLAIM_EXTRACTOR_SYSTEM_PROMPT,
                temperature=0.1
            )
        except Exception as e:
            logger.warning(f"Claim extraction failed for {source_url}: {e}")
            return []

        validated_results = []
        for raw in batch.claims:
            quote = raw.exact_quote.strip()
            if not quote:
                continue

            # Verify and locate the span in original text with 3-tier precision matching
            start, end, prefix, suffix, match_tier, element_role, block_id = WebScraper.locate_quote_spans(clean_text, quote)
            
            if match_tier == "UNVERIFIED":
                logger.debug(f"Quote not verifiable in source text: {quote[:40]}")
            
            res_dict = {
                "statement": raw.statement,
                "claim_type": raw.claim_type,
                "confidence": raw.confidence,
                "reasoning": raw.reasoning,
                "exact_quote": quote,
                "quote_match": match_tier,
                "char_start": start,
                "char_end": end,
                "context_prefix": prefix,
                "context_suffix": suffix,
                "element_role": element_role,
                "block_id": block_id,
            }
            if raw.provenance:
                res_dict["provenance"] = {
                    "relation": raw.provenance.relation,
                    "target_source_id": raw.provenance.target_source_id,
                    "evidence_quote": raw.provenance.evidence_quote
                }
            
            validated_results.append(res_dict)

        return validated_results
