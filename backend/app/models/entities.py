import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Float, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class InvestigationEntity(Base):
    __tablename__ = "investigations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    target_query = Column(Text, nullable=False)
    target_type = Column(String(50), nullable=False, default="GENERAL")
    status = Column(String(50), nullable=False, default="PENDING")
    progress_percentage = Column(Integer, nullable=False, default=0)
    current_stage = Column(String(100), default="INITIALIZING")
    depth = Column(String(20), nullable=False, default="STANDARD")
    config = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sources = relationship("SourceEntity", back_populates="investigation", cascade="all, delete-orphan")
    claims = relationship("ClaimEntity", back_populates="investigation", cascade="all, delete-orphan")
    report = relationship("ReportEntity", back_populates="investigation", uselist=False, cascade="all, delete-orphan")

class SourceEntity(Base):
    __tablename__ = "sources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    investigation_id = Column(String(36), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False)
    url = Column(Text, nullable=False)
    domain = Column(String(255), nullable=False)
    title = Column(Text, nullable=True)
    author = Column(String(255), nullable=True)
    published_at = Column(DateTime, nullable=True)
    retrieved_at = Column(DateTime, default=datetime.utcnow)
    source_type = Column(String(50), nullable=False, default="OTHER")
    content_hash = Column(String(64), nullable=False)
    raw_content = Column(Text, nullable=True)
    clean_text = Column(Text, nullable=False)
    credibility_score = Column(Float, nullable=False, default=0.5)
    source_metadata = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    investigation = relationship("InvestigationEntity", back_populates="sources")
    evidence_snippets = relationship("EvidenceSnippetEntity", back_populates="source", cascade="all, delete-orphan")
    claim_links = relationship("ClaimEvidenceLinkEntity", back_populates="source", cascade="all, delete-orphan")

class EvidenceSnippetEntity(Base):
    __tablename__ = "evidence_snippets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_id = Column(String(36), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    exact_quote = Column(Text, nullable=False)
    char_start = Column(Integer, nullable=True)
    char_end = Column(Integer, nullable=True)
    context_prefix = Column(Text, nullable=True)
    context_suffix = Column(Text, nullable=True)
    embedding_json = Column(JSON, nullable=True)  # Store vector embedding list as JSON for universal SQL/SQLite support
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    source = relationship("SourceEntity", back_populates="evidence_snippets")
    claim_links = relationship("ClaimEvidenceLinkEntity", back_populates="evidence_snippet")

class ClaimEntity(Base):
    __tablename__ = "claims"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    investigation_id = Column(String(36), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False)
    statement = Column(Text, nullable=False)
    claim_type = Column(String(50), nullable=False)  # FACT, INFERENCE, OPINION, UNVERIFIED, CONFLICTING
    confidence = Column(String(20), nullable=False)  # HIGH, MEDIUM, LOW
    verification_status = Column(String(50), nullable=False, default="UNVERIFIED")  # UNVERIFIED, SINGLE_SOURCE, MULTI_SOURCE_SUPPORTED, CONTRADICTED, VERIFIED
    reasoning = Column(Text, nullable=True)
    embedding_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)

    # Relationships
    investigation = relationship("InvestigationEntity", back_populates="claims")
    evidence_links = relationship("ClaimEvidenceLinkEntity", back_populates="claim", cascade="all, delete-orphan")

class ClaimEvidenceLinkEntity(Base):
    __tablename__ = "claim_evidence_links"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    source_id = Column(String(36), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    evidence_snippet_id = Column(String(36), ForeignKey("evidence_snippets.id", ondelete="SET NULL"), nullable=True)
    link_type = Column(String(20), nullable=False, default="SUPPORTING")  # SUPPORTING, CONTRADICTING, MENTIONING
    rationale = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    claim = relationship("ClaimEntity", back_populates="evidence_links")
    source = relationship("SourceEntity", back_populates="claim_links")
    evidence_snippet = relationship("EvidenceSnippetEntity", back_populates="claim_links")

class ReportEntity(Base):
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    investigation_id = Column(String(36), ForeignKey("investigations.id", ondelete="CASCADE"), unique=True, nullable=False)
    title = Column(Text, nullable=False)
    executive_summary = Column(Text, nullable=False)
    markdown_content = Column(Text, nullable=False)
    structured_sections = Column(JSON, nullable=False, default=list)
    citation_map = Column(JSON, nullable=False, default=dict)
    credibility_breakdown = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    investigation = relationship("InvestigationEntity", back_populates="report")
