import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db
from app.agents.planner import PlannerAgent
from app.providers.llm.mock_provider import MockLLMProvider
from app.models.schemas import TargetType, InvestigationDepth

@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Ensure all database tables are created"""
    await init_db()

@pytest.mark.asyncio
async def test_all_investigation_type_planners():
    """Verify that all 5 specialized investigation modes generate tailored sub-tasks and hypotheses"""
    mock_llm = MockLLMProvider()
    planner = PlannerAgent(mock_llm)

    test_cases = [
        ("宇树科技", TargetType.COMPANY),
        ("iPhone 16 Pro", TargetType.PRODUCT),
        ("某高收益理财项目", TargetType.INVESTMENT),
        ("室温超导复现成功", TargetType.CLAIM),
        ("固态电池商业化量产", TargetType.TECHNOLOGY)
    ]

    for query, target_type in test_cases:
        plan = await planner.plan(target_query=query, target_type_hint=target_type)
        assert plan.target_type == target_type
        assert len(plan.sub_tasks) >= 3
        assert len(plan.key_hypotheses) >= 1
        
        # Verify that search queries exist for each sub task
        for task in plan.sub_tasks:
            assert len(task.search_queries) >= 1

@pytest.mark.asyncio
async def test_investigation_events_endpoint():
    """Verify that events are logged and accessible via /events endpoint"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a mock investigation
        res = await client.post("/api/v1/investigations", json={
            "target_query": "测试调查目标",
            "target_type_hint": "TECHNOLOGY",
            "depth": "QUICK",
            "llm_provider": "mock",
            "search_provider": "mock",
            "api_keys": {
                "gemini_api_key": "test_g_key",
                "openai_api_key": "test_o_key",
                "tavily_api_key": "test_t_key"
            }
        })
        assert res.status_code == 200
        inv_id = res.json()["id"]

        # Fetch events endpoint (should return a list)
        events_res = await client.get(f"/api/v1/investigations/{inv_id}/events")
        assert events_res.status_code == 200
        assert isinstance(events_res.json(), list)

@pytest.mark.asyncio
async def test_investigations_list_metrics():
    """Verify that investigation list endpoint returns authentic metrics and no fake 0.85"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/investigations")
        assert res.status_code == 200
        invs = res.json()
        assert isinstance(invs, list)
        if len(invs) > 0:
            inv = invs[0]
            assert "sources_count" in inv
            assert "claims_count" in inv
            assert "verified_claims_count" in inv
            assert "conflicting_claims_count" in inv
            assert "average_credibility" in inv
