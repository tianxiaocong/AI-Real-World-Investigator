import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models.entities import Base, InvestigationEntity, ReportEntity
from app.models.schemas import SourceCreate, SourceType
from app.pipeline.orchestrator import InvestigationOrchestrator

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_full_pipeline_with_mock_providers(db_session: AsyncSession):
    # 1. Create initial investigation record
    inv = InvestigationEntity(
        title="Test Investigation: QuantumTech Corp",
        target_query="QuantumTech Corp",
        target_type="COMPANY",
        depth="STANDARD",
        status="PENDING",
        progress_percentage=0
    )
    db_session.add(inv)
    await db_session.commit()
    await db_session.refresh(inv)

    # 2. Mock WebScraper to return deterministic test content without internet latency
    mock_source = SourceCreate(
        url="https://www.reuters.com/business/quantumtech-analysis",
        domain="reuters.com",
        title="QuantumTech Corp Reports Strong Annual Growth",
        source_type=SourceType.NEWS,
        credibility_score=0.88,
        clean_text="QuantumTech Corp raised $50M in Series B led by Alpha Ventures in 2024. The CEO announced revenue surpassed $100M.",
        content_hash="mockhash123456",
        raw_content="<html><body>QuantumTech Corp raised $50M in Series B...</body></html>"
    )

    with patch("app.pipeline.orchestrator.WebScraper.fetch_and_extract", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_source
        
        # 3. Run Orchestrator with mock providers
        orchestrator = InvestigationOrchestrator(
            db=db_session,
            llm_provider_name="mock",
            search_provider_name="mock"
        )
        await orchestrator.run(inv.id)

    # 4. Verify that investigation completed successfully
    await db_session.refresh(inv)
    assert inv.status == "COMPLETED"
    assert inv.progress_percentage == 100
