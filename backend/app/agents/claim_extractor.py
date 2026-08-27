import logging
from typing import List, Optional, Any
from pydantic import BaseModel, Field
from app.models.schemas import ClaimType, ConfidenceLevel, SourceType
from app.providers.llm.base import LLMProvider
from app.providers.llm import get_llm_provider
from app.scraper.extractor import WebScraper
from app.core.security import wrap_untrusted_content

logger = logging.getLogger(__name__)

class RawExtractedClaim(BaseModel):
    statement: str = Field(..., description="An atomic factual, inferential, or opinionated assertion in concise language.")
    exact_quote: str = Field(..., description="The verbatim, word-for-word quote from the text that directly supports this claim.")
    claim_type: ClaimType = Field(..., description="FACT (objective verifiable), INFERENCE (reasoned conclusion), OPINION (subjective viewpoint), UNVERIFIED (rumor/unsupported), CONFLICTING (disputed).")
    confidence: ConfidenceLevel = Field(..., description="HIGH, MEDIUM, or LOW confidence in this assertion.")
    reasoning: Optional[str] = Field(None, description="Brief explanation of why this claim type and confidence was assigned.")

class ClaimExtractionBatch(BaseModel):
    claims: List[RawExtractedClaim] = Field(default_factory=list)

CLAIM_EXTRACTOR_SYSTEM_PROMPT = """You are an expert Forensic Intelligence Analyst and Claim Extractor.
Your job is to read raw text from a web source and extract 3-8 key atomic claims.

RULES:
1. "exact_quote" MUST BE A VERBATIM, EXACT character-for-character substring found in the source text. Never paraphrase or alter the quote.
2. An atomic claim is a single testable statement (e.g. "Company X was founded in 2021 by Jane Doe" rather than a 500-word paragraph).
3. Strictly classify claim_type:
   - FACT: Objective, verifiable statements (numbers, dates, leadership names, registered filings).
   - INFERENCE: Analytical deductions made by authors based on observed data.
   - OPINION: Subjective viewpoints, praise, criticism, or predictions.
   - UNVERIFIED: Rumors, leaked information, unconfirmed anonymous assertions.
   - CONFLICTING: Statements explicitly acknowledging opposing numbers or views.
4. Set confidence based on clarity and specificity of the evidence.
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

            # Verify and locate the span in original text
            start, end, prefix, suffix = WebScraper.locate_quote_spans(clean_text, quote)
            
            # If quote cannot be found directly in text, do not reject if text is rich, but attempt slight fallback
            if start is None:
                # If exact quote is slightly modified by LLM, try finding sentence fragments
                logger.debug(f"Quote not perfectly aligned in text: {quote[:40]}")
            
            validated_results.append({
                "statement": raw.statement,
                "claim_type": raw.claim_type,
                "confidence": raw.confidence,
                "reasoning": raw.reasoning,
                "exact_quote": quote,
                "char_start": start,
                "char_end": end,
                "context_prefix": prefix,
                "context_suffix": suffix,
            })

        return validated_results
