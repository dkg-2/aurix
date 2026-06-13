import os
import sys
import json
import time
from datetime import datetime
from aurix_worker import AurixWorker
from engine import orchestrate_scan

# Repositories to Baseline
BASELINE_REPOS = [
    "https://github.com/appsecco/dvna",
    "https://github.com/we45/Vulnerable-Flask-App",
    "https://github.com/stamparm/DSVW",
    "https://github.com/fportantier/vulpy",
    "https://github.com/payatu/Tiredful-API",
    "https://github.com/adeyosemanputra/pygoat",
    "https://github.com/OWASP/NodeGoat",
    "https://github.com/juice-shop/juice-shop",
    "https://github.com/WebGoat/WebGoat",
    "https://github.com/digininja/DVWA",
    "https://github.com/OWASP/railsgoat",
    "https://github.com/s4n7h0/vampi"
]

class BaselineRunner:
    def __init__(self):
        self.report_dir = "baseline-reports"
        os.makedirs(self.report_dir, exist_ok=True)

    def run_fast_baseline(self, repo_url):
        print(f"\n🚀 [BASELINE] Starting Fast-Triage for: {repo_url}")
        start_time = time.time()
        
        try:
            # Step 1: Run Phase 1 Static Scan
            raw_report = orchestrate_scan(repo_url, cleanup=False)
            if not raw_report:
                print(f"❌ [ERROR] Scan failed for {repo_url}")
                return

            scan_id = raw_report['scan_id']
            all_findings = raw_report['findings']
            
            # Step 2: Extract findings for a quick Triage-only Summary
            # In an industry-grade setup, we'd invoke the Logic Agent here 
            # to verify if the static findings are likely true positives.
            # For now, we gather the "Raw Intelligent Baseline".
            
            summary = {
                "scan_id": scan_id,
                "url": repo_url,
                "timestamp": datetime.now().isoformat(),
                "duration_sec": round(time.time() - start_time, 2),
                "total_raw_findings": len(all_findings),
                "categories": {}
            }
            
            for f in all_findings:
                cat = f.get('title', 'Unknown')
                summary['categories'][cat] = summary['categories'].get(cat, 0) + 1

            output_path = os.path.join(self.report_dir, f"baseline_{scan_id}.json")
            with open(output_path, "w") as f:
                json.dump(summary, f, indent=2)

            print(f"✅ [DONE] {repo_url} processed in {summary['duration_sec']}s. Findings: {len(all_findings)}")
            return summary

        except Exception as e:
            print(f"❌ [CRITICAL] Failed to process {repo_url}: {str(e)}")

    def run_all(self):
        print(f"=== AURIX BASELINE RUNNER v1.0 ===")
        print(f"Total Repos: {len(BASELINE_REPOS)}")
        
        results = []
        for repo in BASELINE_REPOS:
            res = self.run_fast_baseline(repo)
            if res: results.append(res)
            
        print(f"\n🏆 Baseline Complete! All reports saved in /{self.report_dir}")

if __name__ == "__main__":
    runner = BaselineRunner()
    runner.run_all()
