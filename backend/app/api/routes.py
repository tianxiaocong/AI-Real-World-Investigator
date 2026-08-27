import asyncio
import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_db, AsyncSessionLocal
from app.models.entities import (
    InvestigationEntity, SourceEntity, ClaimEntity,
    ClaimEvidenceLinkEntity, ReportEntity, EvidenceSnippetEntity,
    InvestigationEventEntity
)
from app.models.schemas import (
    InvestigationCreateRequest, InvestigationSummaryResponse,
    ReportResponse, ClaimResponse, SourceResponse, EventLogResponse,
    InvestigationStatus, ClaimType, VerificationStatus, StreamEvent
)
from app.pipeline.orchestrator import (
    InvestigationOrchestrator, get_or_create_event_queue, remove_event_queue
)

from app.models.verification_models import (
    OverallCoverage, InputType
)
from app.agents.fast_verifier import FastClaimVerifierAgent
from app.providers.llm import get_llm_provider
from app.providers.search import get_search_provider
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()

class FastVerifyRequest(BaseModel):
    claim: str = Field(description="用户输入的待核验文本、陈述或问题")
    input_type: Optional[InputType] = Field(default=InputType.TEXT, description="输入类型: TEXT/URL/IMAGE")
    llm_provider: Optional[str] = Field(default="mock", description="LLM 提供商")
    search_provider: Optional[str] = Field(default="mock", description="搜索提供商")
    api_keys: Optional[dict] = Field(default=None, description="动态 API 密钥")

@router.post("/verify", response_model=OverallCoverage)
async def fast_verify_claim(req: FastVerifyRequest):
    """
    快速事实核验核心接口：一句话输入 → 主张拆解 → 溯源去重 → 规则引擎判定 → 结构化 Verdict
    """
    api_k = req.api_keys or {}
    gemini_k = api_k.get("gemini_api_key")
    openai_k = api_k.get("openai_api_key")
    tavily_k = api_k.get("tavily_api_key")
    
    chosen_key = gemini_k if req.llm_provider == "gemini" else openai_k
    llm = get_llm_provider(req.llm_provider, tier="reasoning", api_key=chosen_key)
    search = get_search_provider(req.search_provider, api_key=tavily_k)
    
    agent = FastClaimVerifierAgent(llm_provider=llm, search_provider=search)
    coverage = await agent.verify_input(
        input_text=req.claim,
        input_type=req.input_type or InputType.TEXT
    )
    return coverage

async def run_investigation_in_background(
    investigation_id: str,
    llm_provider: Optional[str] = None,
    search_provider: Optional[str] = None,
    api_keys: Optional[dict] = None
):
    """Background runner with its own dedicated async DB session and dynamic API keys"""
    async with AsyncSessionLocal() as session:
        orchestrator = InvestigationOrchestrator(
            db=session,
            llm_provider_name=llm_provider,
            search_provider_name=search_provider,
            api_keys=api_keys
        )
        await orchestrator.run(investigation_id)

@router.post("/investigations", response_model=InvestigationSummaryResponse)
async def create_investigation(
    req: InvestigationCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Initiate a new investigation with configured search & llm providers"""
    inv = InvestigationEntity(
        title=f"调查: {req.target_query}",
        target_query=req.target_query,
        target_type=req.target_type_hint.value if req.target_type_hint else "GENERAL",
        depth=req.depth.value,
        status=InvestigationStatus.PENDING.value,
        progress_percentage=0,
        current_stage="任务已排队...",
        config={
            "llm_provider": req.llm_provider,
            "search_provider": req.search_provider
        }
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)

    # Launch background task with user-provided API keys
    background_tasks.add_task(
        run_investigation_in_background,
        investigation_id=inv.id,
        llm_provider=req.llm_provider,
        search_provider=req.search_provider,
        api_keys=req.api_keys
    )

    return InvestigationSummaryResponse(
        id=inv.id,
        title=inv.title,
        target_query=inv.target_query,
        target_type=inv.target_type,  # type: ignore
        status=inv.status,  # type: ignore
        progress_percentage=inv.progress_percentage,
        current_stage=inv.current_stage or "",
        depth=inv.depth,  # type: ignore
        error_message=inv.error_message,
        created_at=inv.created_at,
        updated_at=inv.updated_at,
        sources_count=0,
        scraped_sources_count=0,
        claims_count=0,
        verified_claims_count=0,
        conflicting_claims_count=0,
        unverified_claims_count=0,
        average_credibility=None,
        llm_provider=req.llm_provider,
        search_provider=req.search_provider
    )

@router.get("/investigations", response_model=List[InvestigationSummaryResponse])
async def list_investigations(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """List recent investigations with accurate metrics"""
    query = (
        select(InvestigationEntity)
        .options(
            selectinload(InvestigationEntity.sources),
            selectinload(InvestigationEntity.claims),
            selectinload(InvestigationEntity.report)
        )
        .order_by(desc(InvestigationEntity.created_at))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    invs = result.scalars().all()
    
    summaries = []
    for inv in invs:
        s_count = len(inv.sources) if inv.sources else 0
        scraped_count = sum(1 for s in (inv.sources or []) if s.clean_text and len(s.clean_text) > 30)
        c_count = len(inv.claims) if inv.claims else 0
        
        conf_count = sum(1 for c in (inv.claims or []) if c.verification_status in (VerificationStatus.CONFIRMED.value, "MULTI_SOURCE_SUPPORTED", "VERIFIED"))
        prob_count = sum(1 for c in (inv.claims or []) if c.verification_status in (VerificationStatus.PROBABLE.value,))
        sing_count = sum(1 for c in (inv.claims or []) if c.verification_status in (VerificationStatus.SINGLE_SOURCE.value,))
        disp_count = sum(1 for c in (inv.claims or []) if c.verification_status in (VerificationStatus.DISPUTED.value, "CONTRADICTED") or c.claim_type in (ClaimType.DISPUTED.value, "CONFLICTING"))
        unver_count = sum(1 for c in (inv.claims or []) if c.verification_status in (VerificationStatus.UNVERIFIED.value, "UNVERIFIED") or c.claim_type in (ClaimType.RUMOR.value, "RUMOR"))
        
        cite_count = len(inv.report.citation_map) if (inv.report and inv.report.citation_map) else 0
        avg_cred = round(sum(s.credibility_score for s in inv.sources) / len(inv.sources), 2) if inv.sources else None

        cfg = inv.config or {}
        summary = InvestigationSummaryResponse(
            id=inv.id,
            title=inv.title,
            target_query=inv.target_query,
            target_type=inv.target_type,  # type: ignore
            status=inv.status,  # type: ignore
            progress_percentage=inv.progress_percentage,
            current_stage=inv.current_stage or "",
            depth=inv.depth,  # type: ignore
            error_message=inv.error_message,
            created_at=inv.created_at,
            updated_at=inv.updated_at,
            sources_count=s_count,
            scraped_sources_count=scraped_count,
            claims_count=c_count,
            confirmed_claims_count=conf_count,
            probable_claims_count=prob_count,
            single_source_claims_count=sing_count,
            disputed_claims_count=disp_count,
            unverified_claims_count=unver_count,
            verified_claims_count=conf_count + prob_count,
            conflicting_claims_count=disp_count,
            citation_count=cite_count,
            average_credibility=avg_cred,
            llm_provider=cfg.get("llm_provider"),
            search_provider=cfg.get("search_provider")
        )
        summaries.append(summary)

    return summaries

@router.get("/investigations/{investigation_id}", response_model=InvestigationSummaryResponse)
async def get_investigation(investigation_id: str, db: AsyncSession = Depends(get_db)):
    """Get metadata for a single investigation with true credibility & count breakdown"""
    result = await db.execute(
        select(InvestigationEntity)
        .options(
            selectinload(InvestigationEntity.sources),
            selectinload(InvestigationEntity.claims),
            selectinload(InvestigationEntity.report)
        )
        .where(InvestigationEntity.id == investigation_id)
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    s_count = len(inv.sources) if inv.sources else 0
    scraped_count = sum(1 for s in (inv.sources or []) if s.clean_text and len(s.clean_text) > 30)
    c_count = len(inv.claims) if inv.claims else 0
    
    conf_count = sum(1 for c in (inv.claims or []) if c.verification_status in (VerificationStatus.CONFIRMED.value, "MULTI_SOURCE_SUPPORTED", "VERIFIED"))
    prob_count = sum(1 for c in (inv.claims or []) if c.verification_status in (VerificationStatus.PROBABLE.value,))
    sing_count = sum(1 for c in (inv.claims or []) if c.verification_status in (VerificationStatus.SINGLE_SOURCE.value,))
    disp_count = sum(1 for c in (inv.claims or []) if c.verification_status in (VerificationStatus.DISPUTED.value, "CONTRADICTED") or c.claim_type in (ClaimType.DISPUTED.value, "CONFLICTING"))
    unver_count = sum(1 for c in (inv.claims or []) if c.verification_status in (VerificationStatus.UNVERIFIED.value, "UNVERIFIED") or c.claim_type in (ClaimType.RUMOR.value, "RUMOR"))
    
    cite_count = len(inv.report.citation_map) if (inv.report and inv.report.citation_map) else 0
    avg_cred = round(sum(s.credibility_score for s in inv.sources) / len(inv.sources), 2) if inv.sources else None
    cfg = inv.config or {}

    return InvestigationSummaryResponse(
        id=inv.id,
        title=inv.title,
        target_query=inv.target_query,
        target_type=inv.target_type,  # type: ignore
        status=inv.status,  # type: ignore
        progress_percentage=inv.progress_percentage,
        current_stage=inv.current_stage or "",
        depth=inv.depth,  # type: ignore
        error_message=inv.error_message,
        created_at=inv.created_at,
        updated_at=inv.updated_at,
        sources_count=s_count,
        scraped_sources_count=scraped_count,
        claims_count=c_count,
        confirmed_claims_count=conf_count,
        probable_claims_count=prob_count,
        single_source_claims_count=sing_count,
        disputed_claims_count=disp_count,
        unverified_claims_count=unver_count,
        verified_claims_count=conf_count + prob_count,
        conflicting_claims_count=disp_count,
        citation_count=cite_count,
        average_credibility=avg_cred,
        llm_provider=cfg.get("llm_provider"),
        search_provider=cfg.get("search_provider")
    )

@router.get("/investigations/{investigation_id}/events", response_model=List[EventLogResponse])
async def get_investigation_events(investigation_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve full chronological investigation event history from database"""
    result = await db.execute(
        select(InvestigationEventEntity)
        .where(InvestigationEventEntity.investigation_id == investigation_id)
        .order_by(InvestigationEventEntity.created_at.asc())
    )
    events = result.scalars().all()
    return [
        EventLogResponse(
            id=e.id,
            investigation_id=e.investigation_id,
            event_type=e.event_type,
            stage=e.stage,
            progress_percentage=e.progress_percentage,
            data=e.data or {},
            created_at=e.created_at
        )
        for e in events
    ]

@router.get("/investigations/{investigation_id}/stream")
async def stream_investigation_events(investigation_id: str):
    """Server-Sent Events (SSE) stream for real-time investigation progress and discoveries"""
    queue = get_or_create_event_queue(investigation_id)

    async def event_generator():
        try:
            # Yield initial connect ping
            init_event = StreamEvent(
                event_type="connected",
                stage="INITIALIZING",
                progress=0,
                data={"message": f"Connected to live radar stream for {investigation_id}"}
            )
            yield f"event: {init_event.event_type}\ndata: {json.dumps(init_event.model_dump(), default=str)}\n\n"

            while True:
                try:
                    event: StreamEvent = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield f"event: {event.event_type}\ndata: {json.dumps(event.model_dump(), default=str)}\n\n"
                    if event.event_type in ("completed", "error"):
                        break
                except asyncio.TimeoutError:
                    # Keepalive heartbeat
                    yield f": heartbeat\n\n"
        finally:
            remove_event_queue(investigation_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/investigations/{investigation_id}/report", response_model=ReportResponse)
async def get_investigation_report(investigation_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch the final compiled report and citation map"""
    result = await db.execute(
        select(ReportEntity).where(ReportEntity.investigation_id == investigation_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not generated yet or investigation still in progress.")

    return ReportResponse.model_validate(report)

@router.get("/investigations/{investigation_id}/claims", response_model=List[ClaimResponse])
async def get_investigation_claims(
    investigation_id: str,
    claim_type: Optional[ClaimType] = None,
    status: Optional[VerificationStatus] = None,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all claims with evidence links and source details"""
    query = (
        select(ClaimEntity)
        .options(
            selectinload(ClaimEntity.evidence_links).selectinload(ClaimEvidenceLinkEntity.source),
            selectinload(ClaimEntity.evidence_links).selectinload(ClaimEvidenceLinkEntity.evidence_snippet)
        )
        .where(ClaimEntity.investigation_id == investigation_id)
    )
    if claim_type:
        query = query.where(ClaimEntity.claim_type == claim_type.value)
    if status:
        query = query.where(ClaimEntity.verification_status == status.value)

    result = await db.execute(query)
    claims = result.scalars().all()

    responses = []
    for c in claims:
        links = []
        for l in (c.evidence_links or []):
            if l.source and l.evidence_snippet:
                links.append({
                    "id": l.id,
                    "claim_id": c.id,
                    "source_id": l.source.id,
                    "source_url": l.source.url,
                    "source_domain": l.source.domain,
                    "source_title": l.source.title,
                    "source_credibility": l.source.credibility_score,
                    "source_type": l.source.source_type,
                    "exact_quote": l.evidence_snippet.exact_quote,
                    "link_type": l.link_type,
                    "rationale": l.rationale
                })

        meta = c.claim_metadata or {}
        responses.append(
            ClaimResponse(
                id=c.id,
                investigation_id=c.investigation_id,
                statement=c.statement,
                claim_type=c.claim_type,  # type: ignore
                confidence=c.confidence,  # type: ignore
                verification_status=c.verification_status,  # type: ignore
                reasoning=c.reasoning,
                verdict_summary=meta.get("verdict_summary") or c.verification_status,
                verdict_reasons=meta.get("verdict_reasons", []),
                independent_sources_count=meta.get("independent_sources_count", 1),
                source_tiers_summary=meta.get("source_tiers_summary", {}),
                contradictions=meta.get("contradictions", []),
                contradicting_claims=meta.get("contradictions", []),
                created_at=c.created_at,
                verified_at=c.verified_at,
                evidence_links=links  # type: ignore
            )
        )

    return responses

@router.get("/investigations/{investigation_id}/sources", response_model=List[SourceResponse])
async def get_investigation_sources(investigation_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve all scraped sources and credibility scores"""
    result = await db.execute(
        select(SourceEntity).where(SourceEntity.investigation_id == investigation_id)
    )
    sources = result.scalars().all()
    return [
        SourceResponse(
            id=s.id,
            investigation_id=s.investigation_id,
            url=s.url,
            domain=s.domain,
            title=s.title,
            author=s.author,
            published_at=s.published_at,
            source_type=s.source_type,  # type: ignore
            credibility_score=s.credibility_score,
            source_metadata=s.source_metadata or {},
            retrieved_at=s.retrieved_at,
            created_at=s.created_at
        )
        for s in sources
    ]

@router.get("/investigations/{investigation_id}/export")
async def export_investigation(
    investigation_id: str,
    format: str = Query("markdown", enum=["markdown", "json"]),
    db: AsyncSession = Depends(get_db)
):
    """Export the report as Markdown or JSON"""
    result = await db.execute(
        select(ReportEntity).where(ReportEntity.investigation_id == investigation_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if format == "markdown":
        return Response(
            content=report.markdown_content,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=investigation_{investigation_id}.md"}
        )
    else:
        report_dict = {
            "title": report.title,
            "executive_summary": report.executive_summary,
            "sections": report.structured_sections,
            "citation_map": report.citation_map,
            "credibility_breakdown": report.credibility_breakdown,
            "created_at": str(report.created_at)
        }
        return Response(
            content=json.dumps(report_dict, indent=2, ensure_ascii=False),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=investigation_{investigation_id}.json"}
        )
