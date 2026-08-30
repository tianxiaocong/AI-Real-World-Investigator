"""
AI Claim Verifier — Core Data Models (v4 Final)

4 核心实体: Claim, Source, Evidence, Verdict
2 支撑实体: SourceProvenance, EvidenceAssessment

设计原则：
- Verdict 是证据状态，不是真假判断
- 规则引擎判定，LLM 只负责解释
- 没有支持证据 ≠ UNSUPPORTED（UNSUPPORTED 必须有实际反证）
- 独立来源数量 ≠ 证据强度（还需要质量 + 直接性 + scope 匹配）
- 不显示伪精确的 confidence score
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel


# ──────────────────────────────────────────────
#  Enums
# ──────────────────────────────────────────────

class InputType(str, Enum):
    TEXT = "TEXT"
    URL = "URL"
    IMAGE = "IMAGE"


class Verifiability(str, Enum):
    """该声明在公开资料层面的理论可验证性。仅用于解释，不直接影响 Verdict。"""
    PUBLICLY_VERIFIABLE = "PUBLICLY_VERIFIABLE"         # 通常应有公开证据
    LIMITED_PUBLIC = "LIMITED_PUBLIC"                     # 可能有少量公开信息
    HARD_TO_VERIFY = "HARD_TO_VERIFY"                    # 很可能没有完整公开证据
    NOT_PUBLICLY_VERIFIABLE = "NOT_PUBLICLY_VERIFIABLE"   # 无法通过公开资料判断


class SourceTier(str, Enum):
    """来源类型分类。不是可信度评分，是来源性质。"""
    OFFICIAL = "OFFICIAL"           # 官方一手来源（公司公告、政府文件、监管披露）
    AUTHORITATIVE = "AUTHORITATIVE" # 权威媒体（Reuters, Bloomberg, AP）
    MAINSTREAM = "MAINSTREAM"       # 主流媒体
    INDUSTRY = "INDUSTRY"           # 行业/垂直媒体
    COMMUNITY = "COMMUNITY"         # 社区/论坛/自媒体
    UNKNOWN = "UNKNOWN"


class ProvenanceType(str, Enum):
    """Source 的信息溯源类型。"""
    ORIGINAL = "ORIGINAL"           # 这就是原始来源
    CITES = "CITES"                 # 引用了某个原始来源
    REPUBLISHES = "REPUBLISHES"     # 转载
    DERIVED_FROM = "DERIVED_FROM"   # 基于原始数据做了加工/推算
    UNKNOWN = "UNKNOWN"


class EvidenceDirectness(str, Enum):
    """证据对 Claim 的直接程度。"""
    DIRECT = "DIRECT"               # 直接陈述/确认 Claim 的内容
    INDIRECT = "INDIRECT"           # 间接提及（如"据知情人士透露"）
    CONTEXTUAL = "CONTEXTUAL"       # 相关背景信息，但不直接证实/反驳


class ScopeIssueType(str, Enum):
    QUANTIFIER = "QUANTIFIER"
    CONDITION = "CONDITION"
    EXCEPTION = "EXCEPTION"
    POPULATION = "POPULATION"
    TEMPORAL = "TEMPORAL"
    ENTITY_VERSION = "ENTITY_VERSION"


class ScopeSeverity(str, Enum):
    HIGH = "HIGH"
    LOW = "LOW"


class ScopeIssue(BaseModel):
    issue_type: ScopeIssueType
    severity: ScopeSeverity
    source_fragment: str = ""
    claim_fragment: str = ""
    explanation: str = ""


class EvidenceRole(str, Enum):
    FACTUAL_ASSERTION = "FACTUAL_ASSERTION"
    NAVIGATION_OR_LINK = "NAVIGATION_OR_LINK"
    SPECULATION_OR_QUESTION = "SPECULATION_OR_QUESTION"
    BOILERPLATE = "BOILERPLATE"


class EvidenceState(str, Enum):
    """面向用户的证据状态判断（6 级）。"""
    SUFFICIENT = "SUFFICIENT"         # 🟢 证据充分
    STRONG = "STRONG"                 # 🟢 证据较强
    INSUFFICIENT = "INSUFFICIENT"     # 🟡 证据不足
    CONFLICTING = "CONFLICTING"       # 🟠 证据冲突
    UNSUPPORTED = "UNSUPPORTED"       # 🔴 有可靠证据反驳
    NOT_ASSESSABLE = "NOT_ASSESSABLE" # ⚪ 公开资料无法有效核验


class OverallState(str, Enum):
    """多 Claim 整体覆盖状态。与单 Claim 的 EvidenceState 是不同维度。"""
    FULLY_SUPPORTED = "FULLY_SUPPORTED"         # 全部证据充分/较强
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED" # 部分支持，部分不足
    MIXED = "MIXED"                             # 有支持也有冲突/反驳
    FULLY_UNSUPPORTED = "FULLY_UNSUPPORTED"     # 全部有可靠反证
    NOT_ASSESSABLE = "NOT_ASSESSABLE"           # 无法有效评估


# ──────────────────────────────────────────────
#  核心实体 1: Claim
# ──────────────────────────────────────────────

class ClaimAttributes(BaseModel):
    """
    Claim 的结构化属性，辅助数值冲突检测。
    LLM 尽量提取，但提取失败不阻断核验流程。
    """
    subject: str | None = None          # "OpenAI"
    predicate: str | None = None        # "revenue"
    object_value: str | None = None     # "13 billion USD"
    time_context: str | None = None     # "2025"
    qualifiers: list[str] = []          # ["annual", "reached"]
    polarity: bool = True               # True=肯定, False=否定


class Claim(BaseModel):
    id: str
    original_input: str                 # 用户原始完整输入
    input_type: InputType
    statement: str                      # 拆解后的单条可验证声明
    claim_index: int                    # 在原始输入中的序号 (0, 1, 2...)

    attributes: ClaimAttributes | None = None
    fact_slots: Optional[Any] = None
    verifiability: Verifiability
    verifiability_reason: str           # "该声明涉及上市公司营收，应有公开财务披露"

    verified_as_of: str                 # "2026-08-27"


# ──────────────────────────────────────────────
#  核心实体 2: Source
# ──────────────────────────────────────────────

class Source(BaseModel):
    id: str
    url: str
    domain: str
    title: str
    source_tier: SourceTier
    publish_date: str | None = None     # 唯一的时间字段，Evidence 继承此时间
    is_synthetic: bool = False          # True = mock/demo 数据
    raw_text: Optional[str] = None      # 网页正文原始文本
    content_hash: Optional[str] = None  # SHA-256 唯一正文哈希
    fetch_status: str = "FETCH_SUCCESS" # FETCH_SUCCESS, FETCH_FAILED, SYNTHETIC_MOCK
    fetch_mode: str = "LIVE"            # LIVE, CACHED_FALLBACK, SYNTHETIC


# ──────────────────────────────────────────────
#  支撑实体: SourceProvenance
# ──────────────────────────────────────────────

class SourceProvenance(BaseModel):
    """
    描述一个 Source 的信息溯源。
    独立来源数 = 不同 origin_source_id（或自身为 ORIGINAL）的去重数量。
    不做两两 N×N 比较。
    """
    source_id: str
    origin_source_id: str | None = None   # None = 自己就是原始来源
    provenance_type: ProvenanceType
    explanation: str = ""                  # "该报道注明'据 Bloomberg 消息'"


# ──────────────────────────────────────────────
#  核心实体 3: Evidence
# ──────────────────────────────────────────────

class Evidence(BaseModel):
    id: str
    source_id: str
    claim_id: str

    exact_quote: str                       # 原始精确引文
    context: str = ""                      # 引文上下文

    # 对 Claim 的支持/反驳（两个独立布尔，不允许同时为 True）
    supports_claim: bool | None = None     # True=支持, False=不支持, None=无法判断
    contradicts_claim: bool | None = None  # True=反驳, False=不反驳, None=无法判断

    # 证据直接性
    directness: EvidenceDirectness = EvidenceDirectness.CONTEXTUAL

    # 证据与 Claim 的范围匹配
    scope_match: bool = True               # False = 证据说的不是同一件事

    evidence_note: str = ""                # "该来源确认融资事实，但金额描述为8亿而非10亿"
    
    # 物理 Raw-Text 定位与字符级坐标
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    match_tier: str = "UNVERIFIED"         # EXACT, NORMALIZED_EXACT, FUZZY, UNVERIFIED
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    
    # Scope Metadata
    scope_issues: list[ScopeIssue] = []
    
    # Admissibility & Roles
    evidence_role: EvidenceRole = EvidenceRole.FACTUAL_ASSERTION
    is_admissible_factual_evidence: bool = True
    
    # DOM Provenance Metadata
    element_role: str = "MAIN"             # MAIN, ASIDE, NAV, FOOTER, HEADER, etc.
    block_id: str = ""                     # e.g., "aside.related-links"


# ──────────────────────────────────────────────
#  支撑实体: EvidenceAssessment
#  （规则引擎的中间计算结果，不直接展示给用户）
# ──────────────────────────────────────────────

class EvidenceAssessment(BaseModel):
    claim_id: str

    # 来源统计
    total_sources_found: int = 0
    independent_source_count: int = 0      # 去重后的独立信息源
    origin_source_count: int = 0           # 原始来源数
    republish_count: int = 0               # 转载/引用数

    # 证据统计
    supporting_evidence_count: int = 0
    contradicting_evidence_count: int = 0
    context_only_count: int = 0

    # 支持侧质量（必须区分检索到的独立源 vs 真正提供直接支持的独立源）
    has_direct_support: bool = False        # 是否有 directness=DIRECT 且 scope_match=True 的支持
    direct_supporting_origin_count: int = 0 # 真正提供 DIRECT 支持的独立 origin 数量
    has_strong_independent_support: bool = False  # ≥2 独立 origin 直接支持
    has_supporting_official_source: bool = False  # 官方来源是否 **直接支持** 该 Claim

    # 反驳侧质量
    has_credible_contradicting_evidence: bool = False  # 是否有 **可信来源直接反驳**

    # 一致性
    time_consistent: bool | None = None     # 证据时间是否与 Claim 时间一致
    value_consistent: bool | None = None    # 数值/口径是否一致


# ──────────────────────────────────────────────
#  核心实体 4: Verdict
# ──────────────────────────────────────────────

class Verdict(BaseModel):
    claim_id: str
    evidence_state: EvidenceState

    # "为什么这样判断？"（结构化清单，由 LLM 翻译规则结果成人话）
    why_reasons: list[str] = []
    # 例: ["✓ 3 个独立来源支持该说法",
    #       "! 不同来源对金额描述不一致",
    #       "⚠ 尚未找到投资方独立确认"]

    # 证据缺口
    evidence_gaps: list[str] = []

    # 下一步建议（按 Claim 类型动态生成）
    next_step_advice: str = ""

    # 时间有效性
    verified_as_of: str = ""               # "截至 2026-08-27"

    # 完整审计证据链与溯源元数据 (Auditable Evidence Chain & Provenance)
    assessment: Optional[EvidenceAssessment] = None
    sources: list[Source] = []
    evidences: list[Evidence] = []
    provenances: list[SourceProvenance] = []
    fact_slots: Optional[Any] = None
    relations: list[Any] = []
    multi_round_audit: Optional[Dict[str, Any]] = None


# ──────────────────────────────────────────────
#  OverallCoverage（多 Claim 汇总）
# ──────────────────────────────────────────────

class OverallCoverage(BaseModel):
    original_input: str
    input_type: InputType

    claims: list[Claim] = []
    verdicts: list[Verdict] = []

    overall_state: OverallState = OverallState.NOT_ASSESSABLE

    sufficient_count: int = 0
    strong_count: int = 0
    insufficient_count: int = 0
    conflicting_count: int = 0
    unsupported_count: int = 0
    not_assessable_count: int = 0

    coverage_summary: str = ""
    # "你提供的说法包含 3 个可验证事实，其中 2 个证据充分，1 个证据不足。"


Verdict.model_rebuild()
OverallCoverage.model_rebuild()
