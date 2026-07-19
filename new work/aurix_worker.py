import os
import json
import sys
import requests
from datetime import datetime

# Import local components
from engine import orchestrate_scan
from aurix_graph import aurix_engine

class AurixWorker:
    """
    Master Worker that triggers the LangGraph Engine.
    """
    def __init__(self):
        self.results_dir = "verified-results"
        os.makedirs(self.results_dir, exist_ok=True)

    def run_full_audit(self, repo_url):
        # 1. Run Phase 1: Raw Scanning
        print(f"\n[STEP 1] Running multi-layer scan engine for: {repo_url}")
        raw_report = orchestrate_scan(repo_url, cleanup=False)
        if not raw_report: return {"error": "Scan failed"}

        scan_id = raw_report['scan_id']
        workspace_path = raw_report['workspace_path']
        all_findings = raw_report['findings']

        # 2. Prepare LangGraph State
        sast_findings = [f for f in all_findings if f['category'] == "sast"]
        
        # Deduplicate per-line to save tokens
        seen_sigs = set()
        representative_findings = []
        for f in sast_findings:
            sig = f"{f['file']}:{f['line']}:{f['title']}"
            if sig not in seen_sigs:
                representative_findings.append(f)
                seen_sigs.add(sig)

        print(f"[STEP 2] Launching LangGraph Orchestrator for {len(representative_findings)} code flaws...")

        initial_state = {
            "workspace_path": workspace_path,
            "target_vulnerabilities": representative_findings,
            "current_vuln": None,
            "verified_reports": [],
            "retries": 0
        }

        # 3. RUN THE GRAPH
        # This executes the entire Attack -> Defense -> Verify cycle
        final_state = aurix_engine.invoke(initial_state)

        # 4. Final Enrichment & Consolidation
        verified_data = {f['id']: f for f in final_state['verified_reports']}
        
        final_findings = []
        for f in all_findings:
            if f['id'] in verified_data:
                f.update(verified_data[f['id']])
            else:
                f['verified'] = False
            final_findings.append(f)

        final_report = {
            "scan_id": scan_id, "url": repo_url, "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_findings": len(final_findings),
                "neutralized_count": sum(1 for f in final_findings if f.get('wargame_status') == "Neutralized"),
                "scan_engine": "Project AURIX LangGraph v1"
            },
            "findings": final_findings
        }
        
        output_path = os.path.join(self.results_dir, f"verified_report_{scan_id}.json")
        with open(output_path, "w") as f:
            json.dump(final_report, f, indent=2)

        # 5. Webhook Handoff (Send to Bhavya's Backend)
        webhook_url = os.getenv("AURIX_WEBHOOK_URL", "http://localhost:8000/api/v1/scans/webhook")
        webhook_token = os.getenv("AURIX_WEBHOOK_TOKEN", "aurix-dev-token")
        
        print(f"\n[STEP 5] Sending JSON Payload to Backend API -> {webhook_url}")
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {webhook_token}"
            }
            response = requests.post(webhook_url, json=final_report, headers=headers, timeout=10)
            if response.status_code == 200:
                print("   [+] Webhook POST successful!")
            else:
                print(f"   [-] Webhook POST failed with status: {response.status_code} - {response.text}")
                self._save_dead_letter(final_report, scan_id)
        except Exception as e:
            print(f"   [-] Webhook Exception: {e}")
            self._save_dead_letter(final_report, scan_id)

        print(f"\n[DONE] LangGraph Audit Complete.")
        print(f"Total Findings: {len(final_findings)}")
        print(f"Neutralized: {final_report['summary']['neutralized_count']}")
        print(f"Report saved locally: {output_path}")
        return final_report

    def _save_dead_letter(self, report, scan_id):
        """Saves reports that failed to sync to the webhook so they can be retried later."""
        dlq_dir = "pending-sync"
        os.makedirs(dlq_dir, exist_ok=True)
        dlq_path = os.path.join(dlq_dir, f"failed_sync_{scan_id}.json")
        with open(dlq_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"   [!] Saved to Dead Letter Queue: {dlq_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python aurix_worker.py <repo_url>")
    else:
        worker = AurixWorker()
        worker.run_full_audit(sys.argv[1])
