import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_fast_verify_api_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/verify",
            json={
                "claim": "宇树科技于2024年完成近10亿元人民币B2轮融资，美团领投",
                "input_type": "TEXT",
                "llm_provider": "mock",
                "search_provider": "mock"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "original_input" in data
        assert "overall_state" in data
        assert "claims" in data
        assert "verdicts" in data
        assert len(data["claims"]) >= 1
        assert len(data["verdicts"]) >= 1
        
        # Verify first verdict has why_reasons and valid evidence_state
        v = data["verdicts"][0]
        assert v["evidence_state"] in [
            "SUFFICIENT", "STRONG", "INSUFFICIENT", "CONFLICTING", "UNSUPPORTED", "NOT_ASSESSABLE"
        ]
        assert len(v["why_reasons"]) >= 1
        assert "verified_as_of" in v
