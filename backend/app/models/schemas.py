from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

def utc_now():
    return datetime.now(timezone.utc)

class ClaimType(str, Enum):
    FACT_STATEMENT = "FACT_STATEMENT"  # 客观事实陈述 (时间、数字、人事、规格、法律事实)
    OPINION = "OPINION"                # 主观观点评估 (观点、预测、评价)
    INFERENCE = "INFERENCE"            # 逻辑分析推断 (基于证据的推导结论)
    RUMOR = "RUMOR"                    # 传闻/未经证实消息 (匿名爆料、坊间传言)
    DISPUTED = "DISPUTED"              # 争议性主张 (多方表述严重不一的主张)
    
    # Backward compatibility alias
    FACT = "FACT_STATEMENT"

class VerificationStatus(str, Enum):
    """
    [LEGACY / COMPATIBILITY LAYER]
    Notice: The canonical ontology of the investigation engine is EvidenceState (defined in
    app.models.verification_models). VerificationStatus is maintained exclusively for backward
    compatibility with legacy API routes and database schemas.
    """
    CONFIRMED = "CONFIRMED"            # 🟢 已确认 (Mapped to SUFFICIENT / STRONG)
    PROBABLE = "PROBABLE"              # 🟢 基本确认 (Mapped to STRONG)
    SINGLE_SOURCE = "SINGLE_SOURCE"    # 🟠 单一来源 (Mapped to INSUFFICIENT)
    DISPUTED = "DISPUTED"              # 🔴 存在争议 (Mapped to CONFLICTING / UNSUPPORTED)
    UNVERIFIED = "UNVERIFIED"          # ⚪ 无法确认 (Mapped to INSUFFICIENT / NOT_ASSESSABLE)
    OPINION_ONLY = "OPINION_ONLY"      # ⚪ 仅为观点 (Mapped to NOT_ASSESSABLE)

    # Backward compatibility aliases
    MULTI_SOURCE_SUPPORTED = "CONFIRMED"
    VERIFIED = "CONFIRMED"
    CONTRADICTED = "DISPUTED"

class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class SourceType(str, Enum):
    OFFICIAL = "OFFICIAL"
    NEWS = "NEWS"
    BLOG = "BLOG"
    SOCIAL_MEDIA = "SOCIAL_MEDIA"
    FORUM = "FORUM"
    REDDIT = "REDDIT"
    DATABASE = "DATABASE"
    ACADEMIC = "ACADEMIC"
    GOVERNMENT = "GOVERNMENT"
    OTHER = "OTHER"

class InvestigationStatus(str, Enum):
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    RESEARCHING = "RESEARCHING"
    EXTRACTING = "EXTRACTING"
    VERIFYING = "VERIFYING"
    SYNTHESIZING = "SYNTHESIZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class InvestigationDepth(str, Enum):
    QUICK = "QUICK"
    STANDARD = "STANDARD"
    DEEP = "DEEP"

class TargetType(str, Enum):
    COMPANY = "COMPANY"
    PERSON = "PERSON"
    PRODUCT = "PRODUCT"
    TECHNOLOGY = "TECHNOLOGY"
    BUSINESS_MODEL = "BUSINESS_MODEL"
    CLAIM = "CLAIM"
    JOB_OPPORTUNITY = "JOB_OPPORTUNITY"
    INVESTMENT = "INVESTMENT"
    GENERAL = "GENERAL"

# --- Evidence Snippet Schema ---
class EvidenceSnippetBase(BaseModel):
    exact_quote: str = Field(..., description="原文中一字不差的引用文本")
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    context_prefix: Optional[str] = None
    context_suffix: Optional[str] = None

class EvidenceSnippetCreate(EvidenceSnippetBase):
    source_id: str

class EvidenceSnippetResponse(EvidenceSnippetBase):
    id: str
    source_id: str
    source_url: Optional[str] = None
    source_domain: Optional[str] = None
    source_title: Optional[str] = None
    source_credibility: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Source Schema ---
class SourceBase(BaseModel):
    url: str
    domain: str
    title: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    source_type: SourceType = SourceType.OTHER
    credibility_score: float = Field(default=0.5, ge=0.0, le=1.0)
    source_metadata: Dict[str, Any] = Field(default_factory=dict)

class SourceCreate(SourceBase):
    raw_content: Optional[str] = None
    raw_text: Optional[str] = None
    clean_text: str
    content_hash: str

class SourceResponse(SourceBase):
    id: str
    investigation_id: str
    raw_text: Optional[str] = None
    clean_text: Optional[str] = None
    retrieved_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Claim Schema ---
class ClaimEvidenceLinkResponse(BaseModel):
    id: str
    claim_id: str
    source_id: str
    source_url: str
    source_domain: str
    source_title: Optional[str] = None
    source_credibility: float
    source_type: SourceType
    exact_quote: str
    link_type: str  # SUPPORTING, CONTRADICTING, MENTIONING
    rationale: Optional[str] = None

class ClaimBase(BaseModel):
    statement: str = Field(..., description="原子化主张/事实描述")
    claim_type: ClaimType
    confidence: ConfidenceLevel
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    reasoning: Optional[str] = None
    verdict_summary: Optional[str] = Field(None, description="核验结论摘要，例如 '🟢 已确认 (2个独立信源)'")
    verdict_reasons: List[str] = Field(default_factory=list, description="结构化核验依据要点清单")
    independent_sources_count: int = Field(default=1, description="独立根域名信源数量")
    source_tiers_summary: Dict[str, int] = Field(default_factory=dict, description="支持信源梯队统计")

class ClaimCreate(ClaimBase):
    investigation_id: str

class ClaimResponse(ClaimBase):
    id: str
    investigation_id: str
    created_at: datetime
    verified_at: Optional[datetime] = None
    evidence_links: List[ClaimEvidenceLinkResponse] = Field(default_factory=list)
    contradictions: List[Dict[str, Any]] = Field(default_factory=list)
    contradicting_claims: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

# --- Research Plan Sub-tasks ---
class SubTask(BaseModel):
    id: str
    dimension: str
    question: str
    search_queries: List[str]
    rationale: str

class ResearchPlan(BaseModel):
    target_type: TargetType
    target_name: str
    key_hypotheses: List[str]
    sub_tasks: List[SubTask]

# --- Report Section ---
class ReportSection(BaseModel):
    section_id: str
    title: str
    content_markdown: str
    claim_ids: List[str] = Field(default_factory=list)

class ReportResponse(BaseModel):
    id: str
    investigation_id: str
    title: str
    executive_summary: str
    markdown_content: str
    structured_sections: List[Dict[str, Any]]
    citation_map: Dict[str, Any]  # e.g., "1": {"claim_id": "...", "source_url": "...", "quote": "..."}
    credibility_breakdown: Dict[str, Any]
    claims_distribution: Optional[Dict[str, Any]] = None
    sources_breakdown: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Investigation Request & Response ---
class InvestigationCreateRequest(BaseModel):
    target_query: str = Field(..., min_length=2, max_length=500, description="调查目标，如 'OpenAI' 或 '某商业模式'")
    depth: InvestigationDepth = InvestigationDepth.STANDARD
    target_type_hint: Optional[TargetType] = None
    llm_provider: Optional[str] = "gemini"
    search_provider: Optional[str] = "duckduckgo"
    api_keys: Optional[Dict[str, str]] = Field(default_factory=dict, description="前端动态传入的 API 密钥")

class InvestigationSummaryResponse(BaseModel):
    id: str
    title: str
    target_query: str
    target_type: TargetType
    status: InvestigationStatus
    progress_percentage: int
    current_stage: str
    depth: InvestigationDepth
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    sources_count: int = 0
    scraped_sources_count: int = 0
    claims_count: int = 0
    confirmed_claims_count: int = 0
    probable_claims_count: int = 0
    single_source_claims_count: int = 0
    disputed_claims_count: int = 0
    unverified_claims_count: int = 0
    # Backward-compatible aliases
    verified_claims_count: int = 0
    conflicting_claims_count: int = 0
    citation_count: int = 0
    average_credibility: Optional[float] = None
    llm_provider: Optional[str] = None
    search_provider: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# --- Investigation Event Log ---
class EventLogResponse(BaseModel):
    id: str
    investigation_id: str
    event_type: str
    stage: str
    progress_percentage: int
    data: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Real-time SSE Stream Event ---
class StreamEvent(BaseModel):
    event_type: str  # progress, log, plan, source_found, claim_extracted, conflict_detected, completed, error
    stage: str
    progress: int
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
