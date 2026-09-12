import os
import json
import sys
import requests
import time
from datetime import datetime

# Import local components
from engine import orchestrate_scan
from aurix_graph import aurix_engine
from context_fetcher import ContextFetcher
from groq_client import AurixGroqClient
from logic_agent import SYSTEM_PROMPT_LOGIC_HYPER_BATCH, format_hyper_batch_prompt

# --- WEBHOOK HELPERS ---

WEBHOOK_COMPLETE_URL = os.getenv("AURIX_WEBHOOK_URL", "http://localhost:8000/api/internal/webhook/scan-complete")
WEBHOOK_PROGRESS_URL = os.getenv("AURIX_PROGRESS_WEBHOOK_URL", "http://localhost:8000/api/internal/webhook/scan-progress")
WEBHOOK_TOKEN = os.getenv("AURIX_WEBHOOK_TOKEN", "aurix-dev-token")

def _post_progress(scan_id, status, message="", progress_pct=0):
    """Sends a real-time status update to Bhavya's backend so the DB moves from PENDING."""
    try:
        payload = {
            "scan_id": scan_id,
            "status": status,
            "message": message,
            "progress": progress_pct,
            "timestamp": datetime.now().isoformat()
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {WEBHOOK_TOKEN}"
        }
        response = requests.post(WEBHOOK_PROGRESS_URL, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            print(f"    [PROGRESS] Sent: {status} ({progress_pct}%) → {message}")
        else:
            print(f"    [PROGRESS] Warning: Backend returned {response.status_code}")
    except Exception as e:
        # Progress updates are non-critical — never crash the scan over them
        print(f"    [PROGRESS] Failed to send (non-fatal): {e}")


class AurixWorker:
    """
    Master Worker that triggers the LangGraph Engine.
    Now with Progress Webhooks and Hyper-Batch Triage.
    """
    def __init__(self):
        self.results_dir = "verified-results"
        os.makedirs(self.results_dir, exist_ok=True)

    def run_full_audit(self, repo_url, scan_id=None):
        start_time = time.time()

        # =====================================================
        # STEP 1: Raw Multi-Tool Scanning
        # =====================================================
        print(f"\n[STEP 1] Running multi-layer scan engine for: {repo_url}")
        _post_progress(scan_id, "SCANNING", "Cloning repository and running static analyzers...", 10)

        raw_report = orchestrate_scan(repo_url, cleanup=False, scan_id=scan_id)
        if not raw_report:
            _post_progress(scan_id, "FAILED", "Static scan engine failed to produce results.", 0)
            return {"error": "Scan failed"}

        scan_id = raw_report['scan_id']
        workspace_path = raw_report['workspace_path']
        all_findings = raw_report['findings']

        _post_progress(scan_id, "SCANNING", f"Static scan complete. Found {len(all_findings)} raw findings.", 30)

        # =====================================================
        # STEP 2: HYPER-BATCH TRIAGE (Single API Call!)
        # =====================================================
        sast_findings = [f for f in all_findings if f['category'] == "sast"]
        
        # Deduplicate per-line to save tokens
        seen_sigs = set()
        representative_findings = []
        for f in sast_findings:
            sig = f"{f['file']}:{f['line']}:{f['title']}"
            if sig not in seen_sigs:
                representative_findings.append(f)
                seen_sigs.add(sig)

        print(f"[STEP 2] Hyper-Batch Triage: {len(representative_findings)} unique SAST findings to analyze...")
        _post_progress(scan_id, "ANALYZING", f"AI Triage: Analyzing {len(representative_findings)} code findings in a single batch...", 40)

        # Fetch context for ALL findings at once
        fetcher = ContextFetcher(workspace_path)
        findings_with_context = []
        for f in representative_findings:
            ctx = fetcher.get_finding_context(f['file'], f['line'])
            findings_with_context.append((f, ctx))

        # --- CHUNKED HYPER-BATCH: Process in groups of 5 to stay under Groq's 8K TPM limit ---
        CHUNK_SIZE = 5
        exploitable_findings = []
        if findings_with_context:
            client = AurixGroqClient()
            total_chunks = (len(findings_with_context) + CHUNK_SIZE - 1) // CHUNK_SIZE
            triage_map = {}

            for chunk_idx in range(total_chunks):
                start = chunk_idx * CHUNK_SIZE
                end = min(start + CHUNK_SIZE, len(findings_with_context))
                chunk = findings_with_context[start:end]

                print(f"    [TRIAGE] Chunk {chunk_idx + 1}/{total_chunks}: Sending {len(chunk)} findings...")
                _post_progress(scan_id, "ANALYZING", f"AI Triage: Chunk {chunk_idx + 1}/{total_chunks} ({start + 1}-{end} of {len(findings_with_context)})...", 40 + int(15 * (chunk_idx / total_chunks)))

                batch_prompt = format_hyper_batch_prompt(chunk)
                full_prompt = f"{SYSTEM_PROMPT_LOGIC_HYPER_BATCH}\n\n{batch_prompt}"

                triage_response = client.call_logic_agent(full_prompt)
                triage_results = triage_response.get("results", [])

                for r in triage_results:
                    fid = r.get("finding_id")
                    if fid:
                        triage_map[fid] = r

            # Filter: only keep findings the AI marked as exploitable with high confidence
            for f, ctx in findings_with_context:
                triage = triage_map.get(f.get('id')) or triage_map.get(f.get('rule_id'))
                if triage and triage.get("is_exploitable") and triage.get("confidence", 0) >= 0.8:
                    f['_triage_reasoning'] = triage.get("reasoning", "")
                    f['_context'] = ctx
                    exploitable_findings.append(f)
                else:
                    reason = "Not found in triage" if not triage else f"Confidence: {triage.get('confidence', 0)}"
                    print(f"    [DROPPED] {f.get('title', 'Unknown')} — {reason}")

            print(f"    [TRIAGE] Result: {len(exploitable_findings)} exploitable / {len(representative_findings)} total")
        
        _post_progress(scan_id, "ANALYZING", f"Triage complete. {len(exploitable_findings)} confirmed exploitable. Starting Red/Blue agents...", 55)

        # =====================================================
        # STEP 3: Run LangGraph ONLY on confirmed exploitable findings
        # =====================================================
        if exploitable_findings:
            print(f"[STEP 3] Launching LangGraph for {len(exploitable_findings)} confirmed vulnerabilities...")

            initial_state = {
                "workspace_path": workspace_path,
                "target_vulnerabilities": exploitable_findings,
                "current_vuln": None,
                "verified_reports": [],
                "retries": 0
            }

            _post_progress(scan_id, "ANALYZING", "Red Agent attacking, Blue Agent patching, Sandbox verifying...", 65)
            final_state = aurix_engine.invoke(initial_state)
            verified_data = {f['id']: f for f in final_state['verified_reports']}
        else:
            print(f"[STEP 3] No exploitable findings — skipping LangGraph entirely.")
            verified_data = {}

        _post_progress(scan_id, "ANALYZING", "Consolidating final report...", 85)

        # =====================================================
        # STEP 4: Final Enrichment & Consolidation
        # =====================================================
        final_findings = []
        for f in all_findings:
            if f['id'] in verified_data:
                f.update(verified_data[f['id']])
            else:
                f['verified'] = False
            final_findings.append(f)

        elapsed = round(time.time() - start_time, 1)
        
        final_report = {
            "scan_id": scan_id, "url": repo_url, "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_findings": len(final_findings),
                "exploitable_count": len(exploitable_findings),
                "neutralized_count": sum(1 for f in final_findings if f.get('wargame_status') == "Neutralized"),
                "scan_engine": "Project AURIX LangGraph v2 (Hyper-Batch)",
                "elapsed_seconds": elapsed
            },
            "findings": final_findings
        }
        
        output_path = os.path.join(self.results_dir, f"verified_report_{scan_id}.json")
        with open(output_path, "w") as f:
            json.dump(final_report, f, indent=2)

        # =====================================================
        # STEP 5: Webhook Handoff (Send to Bhavya's Backend)
        # =====================================================
        print(f"\n[STEP 5] Sending completed JSON Payload to Backend API -> {WEBHOOK_COMPLETE_URL}")
        _post_progress(scan_id, "COMPLETED", f"Scan finished in {elapsed}s. Sending results...", 95)
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {WEBHOOK_TOKEN}"
            }
            response = requests.post(WEBHOOK_COMPLETE_URL, json=final_report, headers=headers, timeout=90)
            if response.status_code == 200:
                print("   [+] Webhook POST successful!")
                _post_progress(scan_id, "COMPLETED", "Results delivered to backend.", 100)
            else:
                print(f"   [-] Webhook POST failed with status: {response.status_code} - {response.text}")
                self._save_dead_letter(final_report, scan_id)
        except Exception as e:
            print(f"   [-] Webhook Exception: {e}")
            self._save_dead_letter(final_report, scan_id)

        print(f"\n[DONE] LangGraph Audit Complete in {elapsed}s.")
        print(f"Total Findings: {len(final_findings)}")
        print(f"Exploitable: {len(exploitable_findings)}")
        print(f"Neutralized: {final_report['summary']['neutralized_count']}")
        print(f"Report saved locally: {output_path}")

        # =====================================================
        # STEP 6: Final Cleanup
        # =====================================================
        print(f"[INFO] Purging temporary workspace to save storage...")
        try:
            import shutil
            def _remove_readonly(func, path, excinfo):
                import stat
                os.chmod(path, stat.S_IWRITE)
                func(path)
            shutil.rmtree(workspace_path, onerror=_remove_readonly)
        except Exception as e:
            print(f"[WARN] Failed to purge workspace: {e}")

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
        print("Usage: python aurix_worker.py <repo_url> [scan_id]")
    else:
        worker = AurixWorker()
        scan_id = sys.argv[2] if len(sys.argv) > 2 else None
        worker.run_full_audit(sys.argv[1], scan_id=scan_id)
