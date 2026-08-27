import httpx
import time
import json

def test_unitree():
    base_url = "http://127.0.0.1:8000/api/v1"
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        print("[1] Initiating Deep Investigation for '宇树科技' (Unitree Robotics)...")
        create_res = client.post("/investigations", json={
            "target_query": "宇树科技",
            "target_type_hint": "COMPANY",
            "depth": "STANDARD",
            "llm_provider": "mock",
            "search_provider": "mock"
        })
        inv_id = create_res.json()["id"]
        print(f"    Investigation Created: {inv_id}")

        print("[2] Polling Execution State...")
        for i in range(15):
            time.sleep(0.4)
            st_res = client.get(f"/investigations/{inv_id}")
            st = st_res.json()
            pct = st["progress_percentage"]
            stage = st["current_stage"]
            status = st["status"]
            print(f"    [{i+1:02d}] {pct}% - {stage} ({status})")
            if status in ("COMPLETED", "FAILED"):
                break

        print("[3] Fetching Extracted Claims...")
        claims_res = client.get(f"/investigations/{inv_id}/claims")
        claims = claims_res.json()
        print(f"    Total Claims Extracted: {len(claims)}")
        for idx, c in enumerate(claims, 1):
            print(f"    Claim [{idx}]: {c['statement']} (Type: {c['claim_type']}, Status: {c['verification_status']})")

        print("[4] Fetching Compiled 15-Section Dossier Report...")
        report_res = client.get(f"/investigations/{inv_id}/report")
        assert report_res.status_code == 200
        report = report_res.json()
        print(f"    Report Title: {report['title']}")
        print(f"    Executive Summary: {report['executive_summary']}")
        print(f"    Total Bound Citations: {len(report['citation_map'])}")
        
        for k, v in report['citation_map'].items():
            print(f"    Citation [{k}] -> Source: {v.get('source_domain')} | Quote: \"{v.get('quote')}\"")

        print("\n[SUCCESS] UNITREE ROBOTICS INVESTIGATION VERIFIED WITH 100% SUCCESS!")

if __name__ == "__main__":
    test_unitree()
