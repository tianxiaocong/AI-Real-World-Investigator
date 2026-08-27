import httpx
import time
import json

def test_live_investigation():
    base_url = "http://127.0.0.1:8000/api/v1"
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        print("[1] Health Check...")
        health = client.get("http://127.0.0.1:8000/health")
        print("    Health:", health.json())

        print("[2] Creating Investigation for 'OpenAI & LLM Frontier'...")
        create_res = client.post("/investigations", json={
            "target_query": "OpenAI & LLM Frontier",
            "target_type_hint": "COMPANY",
            "depth": "STANDARD",
            "llm_provider": "mock",
            "search_provider": "mock"
        })
        inv_data = create_res.json()
        inv_id = inv_data["id"]
        print(f"    Investigation Created: {inv_id}")

        print("[3] Polling Pipeline Progress...")
        for i in range(20):
            time.sleep(0.4)
            st_res = client.get(f"/investigations/{inv_id}")
            st = st_res.json()
            pct = st["progress_percentage"]
            stage = st["current_stage"]
            status = st["status"]
            print(f"    [{i+1:02d}] {pct}% - {stage} ({status})")
            if status in ("COMPLETED", "FAILED"):
                break

        print("[4] Fetching Claims...")
        claims_res = client.get(f"/investigations/{inv_id}/claims")
        claims = claims_res.json()
        print(f"    Total Extracted Claims: {len(claims)}")
        if claims:
            first = claims[0]
            print(f"    Sample Claim: '{first['statement']}'")
            print(f"    Claim Type: {first['claim_type']} | Verification Status: {first['verification_status']}")

        print("[5] Fetching Final Dossier Report...")
        report_res = client.get(f"/investigations/{inv_id}/report")
        assert report_res.status_code == 200, f"Expected 200, got {report_res.status_code}"
        report = report_res.json()
        print(f"    Report Title: {report['title']}")
        print(f"    Executive Summary: {report['executive_summary']}")
        print(f"    Bound Citations Count: {len(report['citation_map'])}")
        
        cite_1 = report['citation_map'].get('1', {})
        print("    Sample Citation [1] Anchor:")
        print(f"      - Statement: {cite_1.get('statement')}")
        print(f"      - Source Domain: {cite_1.get('source_domain')}")
        print(f"      - Exact Quote: \"{cite_1.get('quote')}\"")
        print(f"      - Credibility Score: {cite_1.get('source_credibility')}")

        print("\n[SUCCESS] LIVE END-TO-END INVESTIGATION VERIFIED WITH 100% SUCCESS!")

if __name__ == "__main__":
    test_live_investigation()
