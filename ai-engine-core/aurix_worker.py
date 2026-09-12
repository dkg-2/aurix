"""
AURIX Worker Pipeline v2 — Clean 5-Phase Audit Engine.

Phase 1: Static Scanning (Opengrep, Trivy, Gitleaks, Hadolint)
Phase 2: Smart Triage (Token-aware adaptive batching)
Phase 3: Deep Analysis (LangGraph Red/Blue/Sandbox)
Phase 4: Report Generation & Webhook Delivery
Phase 5: Workspace Cleanup
"""

import os
import sys
import json
import shutil
import stat
import time
import traceback
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

from engine import orchestrate_scan
from aurix_graph import aurix_engine
from context_fetcher import ContextFetcher
from groq_client import call_triage
from logic_agent import SYSTEM_PROMPT_TRIAGE, format_batch_prompt, create_adaptive_chunks

# ═══════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════

WEBHOOK_COMPLETE_URL = os.getenv("AURIX_WEBHOOK_URL")
WEBHOOK_PROGRESS_URL = os.getenv("AURIX_PROGRESS_WEBHOOK_URL")
WEBHOOK_TOKEN = os.getenv("AURIX_WEBHOOK_TOKEN", "aurix-dev-token")
RESULTS_DIR = "verified-results"
DLQ_DIR = "pending-sync"


# ═══════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════

def _post_progress(scan_id, status, message="", progress_pct=0):
    """Sends a real-time status update to the backend. Non-critical — never crashes the scan."""
    if not WEBHOOK_PROGRESS_URL:
        return
    try:
        requests.post(WEBHOOK_PROGRESS_URL, json={
            "scan_id": scan_id, "status": status,
            "message": message, "progress": progress_pct,
            "timestamp": datetime.now().isoformat()
        }, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {WEBHOOK_TOKEN}"
        }, timeout=10)
        print(f"    [PROGRESS] {status} ({progress_pct}%) — {message}")
    except Exception:
        pass


def _save_dead_letter(report, scan_id):
    """Saves failed webhook payloads for manual retry later."""
    os.makedirs(DLQ_DIR, exist_ok=True)
    path = os.path.join(DLQ_DIR, f"failed_sync_{scan_id}.json")
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"    [DLQ] Saved to {path}")


def _remove_readonly(func, path, _):
    """Handler for shutil.rmtree to remove read-only files (git locks on Windows)."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


# ═══════════════════════════════════════════════
# MAIN WORKER CLASS
# ═══════════════════════════════════════════════

class AurixWorker:

    def __init__(self):
        os.makedirs(RESULTS_DIR, exist_ok=True)

    def run_full_audit(self, repo_url, scan_id=None):
        start_time = time.time()

        try:
            # ─────────────────────────────────────────
            # PHASE 1: Static Scanning
            # ─────────────────────────────────────────
            print(f"\n[PHASE 1] Static scanning: {repo_url}")
            _post_progress(scan_id, "SCANNING", "Cloning repository and running static analyzers...", 10)

            raw_report = orchestrate_scan(repo_url, cleanup=False, scan_id=scan_id)
            if not raw_report:
                _post_progress(scan_id, "FAILED", "Static scan engine returned no results.", 0)
                return {"error": "Scan failed"}

            scan_id = raw_report['scan_id']
            workspace_path = raw_report['workspace_path']
            all_findings = raw_report['findings']

            print(f"[PHASE 1] Found {len(all_findings)} raw findings.")
            _post_progress(scan_id, "SCANNING", f"Static scan complete. {len(all_findings)} raw findings.", 30)

            # ─────────────────────────────────────────
            # PHASE 2: Smart Triage (Adaptive Batching)
            # ─────────────────────────────────────────
            sast_findings = [f for f in all_findings if f.get('category') == 'sast']

            # Deduplicate by file:line:title
            seen = set()
            unique_findings = []
            for f in sast_findings:
                sig = f"{f.get('file')}:{f.get('line')}:{f.get('title')}"
                if sig not in seen:
                    unique_findings.append(f)
                    seen.add(sig)

            print(f"[PHASE 2] Triage: {len(unique_findings)} unique SAST findings")
            _post_progress(scan_id, "ANALYZING", f"Triaging {len(unique_findings)} findings...", 35)

            # Fetch code context for all findings
            fetcher = ContextFetcher(workspace_path)
            findings_with_context = []
            for f in unique_findings:
                ctx = fetcher.get_finding_context(f.get('file', ''), f.get('line', 0))
                findings_with_context.append((f, ctx))

            # Create token-aware adaptive chunks
            chunks = create_adaptive_chunks(findings_with_context, max_tokens=5500)
            print(f"    [TRIAGE] Split into {len(chunks)} adaptive chunks")

            # Process each chunk through the triage AI
            triage_map = {}
            for i, chunk in enumerate(chunks):
                print(f"    [TRIAGE] Chunk {i+1}/{len(chunks)}: {len(chunk)} findings")
                _post_progress(scan_id, "ANALYZING",
                    f"Triage chunk {i+1}/{len(chunks)}...",
                    35 + int(20 * (i / max(len(chunks), 1))))

                prompt = f"{SYSTEM_PROMPT_TRIAGE}\n\n{format_batch_prompt(chunk)}"
                response = call_triage(prompt)
                
                for r in response.get("results", []):
                    fid = r.get("finding_id")
                    if fid:
                        triage_map[fid] = r

            # Filter: keep only confirmed exploitable findings
            exploitable_findings = []
            for f, ctx in findings_with_context:
                triage = triage_map.get(f.get('id')) or triage_map.get(f.get('rule_id'))
                if triage and triage.get("is_exploitable") and triage.get("confidence", 0) >= 0.7:
                    f['_triage_reasoning'] = triage.get("reasoning", "")
                    f['_context'] = ctx
                    exploitable_findings.append(f)

            dropped = len(unique_findings) - len(exploitable_findings)
            print(f"    [TRIAGE] Result: {len(exploitable_findings)} exploitable, {dropped} dropped")
            _post_progress(scan_id, "ANALYZING",
                f"Triage done. {len(exploitable_findings)} exploitable findings.", 55)

            # ─────────────────────────────────────────
            # PHASE 3: Deep Analysis (LangGraph)
            # ─────────────────────────────────────────
            verified_data = {}
            if exploitable_findings:
                print(f"[PHASE 3] LangGraph: Analyzing {len(exploitable_findings)} vulnerabilities...")
                _post_progress(scan_id, "ANALYZING", "Red Agent attacking, Blue Agent patching...", 60)

                initial_state = {
                    "workspace_path": workspace_path,
                    "target_vulnerabilities": exploitable_findings,
                    "current_vuln": None,
                    "verified_reports": [],
                    "retries": 0
                }

                final_state = aurix_engine.invoke(initial_state)
                verified_data = {r['id']: r for r in final_state.get('verified_reports', []) if 'id' in r}
            else:
                print(f"[PHASE 3] Skipped — no exploitable findings to analyze.")

            _post_progress(scan_id, "ANALYZING", "Consolidating report...", 85)

            # ─────────────────────────────────────────
            # PHASE 4: Report Generation & Webhook
            # ─────────────────────────────────────────
            # Merge verified data back into all_findings
            final_findings = []
            for f in all_findings:
                if f.get('id') in verified_data:
                    f.update(verified_data[f['id']])
                else:
                    f['verified'] = False
                final_findings.append(f)

            elapsed = round(time.time() - start_time, 1)

            final_report = {
                "scan_id": scan_id,
                "url": repo_url,
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_findings": len(final_findings),
                    "exploitable_count": len(exploitable_findings),
                    "neutralized_count": sum(1 for f in final_findings if f.get('wargame_status') == 'Neutralized'),
                    "scan_engine": "Project AURIX LangGraph v3 (Adaptive Batch)",
                    "elapsed_seconds": elapsed
                },
                "findings": final_findings
            }

            # Save locally
            output_path = os.path.join(RESULTS_DIR, f"verified_report_{scan_id}.json")
            with open(output_path, "w") as f:
                json.dump(final_report, f, indent=2)
            print(f"[PHASE 4] Report saved: {output_path}")

            # Webhook delivery
            if WEBHOOK_COMPLETE_URL:
                try:
                    res = requests.post(WEBHOOK_COMPLETE_URL, json=final_report, headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {WEBHOOK_TOKEN}"
                    }, timeout=90)
                    if res.status_code == 200:
                        print(f"[PHASE 4] Webhook delivered successfully.")
                    else:
                        print(f"[PHASE 4] Webhook failed: {res.status_code}")
                        _save_dead_letter(final_report, scan_id)
                except Exception as e:
                    print(f"[PHASE 4] Webhook exception: {e}")
                    _save_dead_letter(final_report, scan_id)

            _post_progress(scan_id, "COMPLETED", f"Scan complete in {elapsed}s.", 100)

            # ─────────────────────────────────────────
            # PHASE 5: Cleanup
            # ─────────────────────────────────────────
            if workspace_path and os.path.exists(workspace_path):
                try:
                    shutil.rmtree(workspace_path, onerror=_remove_readonly)
                    print(f"[PHASE 5] Workspace cleaned up.")
                except Exception as e:
                    print(f"[PHASE 5] Cleanup failed (non-fatal): {e}")

            print(f"\n{'='*50}")
            print(f"SCAN COMPLETE — {elapsed}s")
            print(f"Total: {len(final_findings)} | Exploitable: {len(exploitable_findings)} | Neutralized: {final_report['summary']['neutralized_count']}")
            print(f"{'='*50}")

            return final_report

        except Exception as e:
            print(f"\n[FATAL] Unhandled exception in audit pipeline:")
            traceback.print_exc()
            _post_progress(scan_id, "FAILED", f"Engine crashed: {str(e)[:200]}", 0)
            return {"error": str(e)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python aurix_worker.py <repo_url_or_zip_path> [scan_id]")
        sys.exit(1)

    target = sys.argv[1]
    sid = sys.argv[2] if len(sys.argv) > 2 else None

    worker = AurixWorker()
    worker.run_full_audit(target, scan_id=sid)
