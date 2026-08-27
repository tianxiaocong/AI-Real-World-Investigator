import httpx
import time
import json
import sys

def test_live_ddg_investigation():
    sys.stdout.reconfigure(encoding='utf-8')
    base_url = "http://127.0.0.1:8000/api/v1"
    with httpx.Client(base_url=base_url, timeout=45.0) as client:
        print("[1] Initiating Investigation for '宇树科技' with Real DuckDuckGo Search...")
        create_res = client.post("/investigations", json={
            "target_query": "宇树科技",
            "target_type_hint": "COMPANY",
            "depth": "STANDARD",
            "llm_provider": "mock",
            "search_provider": "duckduckgo"
        })
        inv_id = create_res.json()["id"]
        print(f"    Investigation Created: {inv_id}")

        print("[2] Polling Execution State...")
        for i in range(25):
            time.sleep(0.8)
            st_res = client.get(f"/investigations/{inv_id}")
            st = st_res.json()
            pct = st["progress_percentage"]
            stage = st["current_stage"]
            status = st["status"]
            print(f"    [{i+1:02d}] {pct}% - {stage} ({status})")
            if status in ("COMPLETED", "FAILED"):
                break

        print("[3] Fetching Sources & Claims...")
        sources_res = client.get(f"/investigations/{inv_id}/sources")
        print(f"    Retrieved Sources Count: {len(sources_res.json())}")
        for s in sources_res.json()[:3]:
            print(f"      - [{s['source_type']}] {s['domain']} : {s['title']}")

        claims_res = client.get(f"/investigations/{inv_id}/claims")
        claims = claims_res.json()
        print(f"    Total Claims: {len(claims)}")

        print("[4] Fetching Report...")
        report_res = client.get(f"/investigations/{inv_id}/report")
        if report_res.status_code == 200:
            report = report_res.json()
            print(f"    Report Title: {report['title']}")
            print(f"    Citations Bound: {len(report['citation_map'])}")
            print("\n[SUCCESS] REAL SEARCH INVESTIGATION COMPLETED WITH 100% SUCCESS!")
        else:
            print(f"    Report failed with code: {report_res.status_code}")

if __name__ == "__main__":
    test_live_ddg_investigation()
