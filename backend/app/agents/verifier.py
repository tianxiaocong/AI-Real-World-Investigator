import logging
import numpy as np
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.models.schemas import VerificationStatus, ClaimType
from app.providers.llm.base import LLMProvider
from app.providers.llm import get_llm_provider

logger = logging.getLogger(__name__)

def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    a = np.array(vec_a, dtype=float)
    b = np.array(vec_b, dtype=float)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

class ConflictJudgement(BaseModel):
    is_conflicting: bool = Field(..., description="True if statement A and statement B present irreconcilable, contradictory facts or figures.")
    is_supporting: bool = Field(..., description="True if statement A and B agree and corroborate each other.")
    explanation: str = Field(..., description="Brief explanation of the consensus or disagreement.")

VERIFIER_SYSTEM_PROMPT = """You are an impartial Supreme Fact Checker and Intelligence Verification Arbiter.
Given two statements regarding the same subject, decide if they:
1. SUPPORT each other (same fact or mutually reinforcing details)
2. CONFLICT with each other (contradictory numbers, dates, outcomes, or opposing claims)
3. NEUTRAL / DIFFERENT ASPECTS (unrelated details)
"""

class VerificationAgent:
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm = llm_provider or get_llm_provider(tier="reasoning")

    async def verify_and_cluster_claims(self, claims_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes raw claims with embeddings and source metadata, clusters similar topics,
        runs LLM cross-examination on candidate duplicates or conflicting pairs,
        and assigns VerificationStatus.
        """
        if not claims_data:
            return []

        # Step 1: Assign initial status based on sources count
        for c in claims_data:
            sources_count = len(c.get("sources", []))
            if sources_count > 1:
                c["verification_status"] = VerificationStatus.MULTI_SOURCE_SUPPORTED
            elif sources_count == 1:
                c["verification_status"] = VerificationStatus.SINGLE_SOURCE
            else:
                c["verification_status"] = VerificationStatus.UNVERIFIED
            c["contradicting_claims"] = []

        # Step 2: Compare pairs with high semantic similarity (> 0.70)
        n = len(claims_data)
        for i in range(n):
            for j in range(i + 1, n):
                c1 = claims_data[i]
                c2 = claims_data[j]

                emb1 = c1.get("embedding")
                emb2 = c2.get("embedding")

                sim = 0.0
                if emb1 and emb2:
                    sim = cosine_similarity(emb1, emb2)

                # If semantically close or targeting the exact same metric
                if sim > 0.75 or (c1["claim_type"] == ClaimType.FACT and c2["claim_type"] == ClaimType.FACT and sim > 0.65):
                    judgement = await self._judge_pair(c1["statement"], c2["statement"])
                    if judgement.is_conflicting:
                        logger.info(f"Conflict detected between: '{c1['statement']}' vs '{c2['statement']}'")
                        c1["verification_status"] = VerificationStatus.CONTRADICTED
                        c2["verification_status"] = VerificationStatus.CONTRADICTED
                        c1["claim_type"] = ClaimType.CONFLICTING
                        c2["claim_type"] = ClaimType.CONFLICTING
                        
                        c1["contradicting_claims"].append({
                            "statement": c2["statement"],
                            "reason": judgement.explanation
                        })
                        c2["contradicting_claims"].append({
                            "statement": c1["statement"],
                            "reason": judgement.explanation
                        })
                    elif judgement.is_supporting:
                        if c1["verification_status"] != VerificationStatus.CONTRADICTED:
                            c1["verification_status"] = VerificationStatus.MULTI_SOURCE_SUPPORTED
                        if c2["verification_status"] != VerificationStatus.CONTRADICTED:
                            c2["verification_status"] = VerificationStatus.MULTI_SOURCE_SUPPORTED

        return claims_data

    async def _judge_pair(self, stmt_a: str, stmt_b: str) -> ConflictJudgement:
        prompt = (
            f"Statement A: \"{stmt_a}\"\n"
            f"Statement B: \"{stmt_b}\"\n\n"
            f"Do these two statements support each other, conflict with each other, or describe unrelated aspects?"
        )
        try:
            return await self.llm.generate_structured(
                prompt=prompt,
                response_model=ConflictJudgement,
                system_prompt=VERIFIER_SYSTEM_PROMPT,
                temperature=0.0
            )
        except Exception as e:
            logger.warning(f"Pair verification error: {e}")
            return ConflictJudgement(is_conflicting=False, is_supporting=False, explanation="Analysis skipped.")
