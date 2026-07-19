import os
import subprocess
import uuid
import shutil
import json
import threading
from datetime import datetime, timezone

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.join(BASE_DIR, "workspace")
RESULTS_DIR = os.path.join(BASE_DIR, "scan-results-automated")
IMAGE_NAME = "security-engine:latest"

# Standard Severity Mapping
SEVERITY_MAP = {
    "CRITICAL": "CRITICAL",
    "HIGH": "HIGH",
    "WARNING": "MEDIUM",
    "MEDIUM": "MEDIUM",
    "LOW": "LOW",
    "INFO": "INFO",
    "ERROR": "HIGH"
}

# Heuristic Risk Scores (CVSS fallback)
HEURISTIC_CVSS = {
    "CRITICAL": 9.5,
    "HIGH": 8.0,
    "MEDIUM": 5.5,
    "LOW": 2.5,
    "INFO": 1.0,
    "UNKNOWN": 0.0
}

def _get_risk_score(raw_sev, raw_cvss):
    """Calculates risk score using available CVSS or severity fallback."""
    try:
        if raw_cvss and float(raw_cvss) > 0:
            return float(raw_cvss)
    except (ValueError, TypeError):
        pass
    std_sev = SEVERITY_MAP.get(raw_sev.upper(), "UNKNOWN") if raw_sev else "UNKNOWN"
    return HEURISTIC_CVSS.get(std_sev, 0.0)

def _load_json(path):
    """Robust JSON loader with multi-encoding support."""
    if not os.path.exists(path):
        return None
    for enc in ['utf-8', 'utf-16', 'utf-8-sig']:
        try:
            with open(path, 'r', encoding=enc) as f:
                data = json.load(f)
                return data if data else None
        except (UnicodeError, json.JSONDecodeError):
            continue
    return None

# --- ENGINE CORE ---

def _run_docker_tool(name, args_str, src_path, output_path):
    """Generic wrapper to execute security tools via Docker."""
    print(f"[INFO] [{name}] Initializing scan...")
    
    # Docker-out-of-Docker Path Resolution Fix
    host_workspace = os.getenv("HOST_WORKSPACE_DIR")
    if host_workspace:
        # If running in Docker, we must map the Host's directory path to the Daemon, not the container's internal path
        folder_name = os.path.basename(src_path)
        # Handle Windows paths correctly if the host is Windows (avoid backslash in f-string expression for Python < 3.12)
        clean_host = host_workspace.rstrip('/\\')
        host_src_path = f"{clean_host}/{folder_name}"
        cmd = f'docker run --rm -v "{host_src_path}:/src" {IMAGE_NAME} {args_str}'
    else:
        cmd = f'docker run --rm -v "{src_path}:/src" {IMAGE_NAME} {args_str}'

    print(f"[DEBUG] Executing: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8')
        stdout = result.stdout.strip()
        
        if result.returncode != 0 and name != "Gitleaks":
            print(f"[WARN] [{name}] Process returned exit code {result.returncode}")

        if stdout:
            # Locate start of JSON object or array to strip potential console noise
            start_idx = min(stdout.find('{') if '{' in stdout else len(stdout), 
                           stdout.find('[') if '[' in stdout else len(stdout))
            clean_json = stdout[start_idx:] if start_idx < len(stdout) else stdout
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(clean_json)
            print(f"[SUCCESS] [{name}] Results captured.")
        else:
            # Ensure an empty valid JSON is present if no findings
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("[]" if name in ["Gitleaks", "Hadolint"] else "{}")
            print(f"[INFO] [{name}] Completed with no findings.")

    except Exception as e:
        print(f"[ERROR] [{name}] Critical system failure: {e}")

def _normalize_results(scan_id, raw_results):
    """Consolidates disparate tool outputs into the Unified Intelligence Schema."""
    unified = []
    
    for tool, path in raw_results.items():
        if tool == "workspace_path": continue # Skip the directory path
        data = _load_json(path)
        if not data: continue
        
        if tool == "opengrep" and 'results' in data:
            for item in data['results']:
                extra = item.get('extra', {})
                metadata = extra.get('metadata', {})
                unified.append({
                    "id": str(uuid.uuid4()), # Truly unique ID per occurrence
                    "rule_id": item.get('check_id'), # Keep original rule ID
                    "tool": "opengrep", "category": "sast",
                    "title": item.get('check_id').split('.')[-1], "description": extra.get('message'),
                    "severity": SEVERITY_MAP.get(extra.get('severity', 'INFO').upper(), "INFO"),
                    "cvss": _get_risk_score(extra.get('severity', 'INFO'), metadata.get('cvss_score', 0.0)),
                    "file": item.get('path'), "line": item.get('start', {}).get('line'),
                    "evidence": extra.get('lines', '').strip(), "fix": extra.get('fix', 'Consult documentation.'),
                    "references": metadata.get('references', [])
                })
        
        elif tool == "trivy" and 'Results' in data:
            for target in data['Results']:
                if 'Vulnerabilities' in target:
                    for vuln in target['Vulnerabilities']:
                        unified.append({
                            "id": vuln.get('VulnerabilityID'), "tool": "trivy", "category": "sca",
                            "title": vuln.get('Title', vuln.get('PkgName')), "description": vuln.get('Description', ''),
                            "severity": SEVERITY_MAP.get(vuln.get('Severity', 'INFO').upper(), "INFO"),
                            "cvss": _get_risk_score(vuln.get('Severity', 'INFO'), vuln.get('CVSS', {}).get('nvd', {}).get('V3Score', 0.0)),
                            "file": target.get('Target'), "line": 0, "evidence": vuln.get('PkgName'),
                            "fix": f"Update to {vuln.get('FixedVersion', 'latest')}", "references": [vuln.get('PrimaryURL')] if vuln.get('PrimaryURL') else []
                        })
        
        elif tool == "gitleaks" and isinstance(data, list):
            for item in data:
                unified.append({
                    "id": item.get('RuleID'), "tool": "gitleaks", "category": "secrets",
                    "title": "Hardcoded Secret", "description": item.get('Description'),
                    "severity": "CRITICAL", "cvss": 9.5, "file": item.get('File'),
                    "line": item.get('StartLine'), "evidence": item.get('Match'),
                    "fix": "Rotate credentials immediately.", "references": []
                })
        
        elif tool == "hadolint" and isinstance(data, list):
            for item in data:
                unified.append({
                    "id": item.get('code'), "tool": "hadolint", "category": "infra",
                    "title": f"Docker Best Practice: {item.get('code')}", "description": item.get('message'),
                    "severity": SEVERITY_MAP.get(item.get('level', 'INFO').upper(), "INFO"),
                    "cvss": 3.0, "file": item.get('file'), "line": item.get('line'),
                    "evidence": item.get('code'), "fix": "Refactor Dockerfile instruction.", "references": []
                })

    return {
        "scan_id": scan_id, "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_findings": len(unified), "findings": unified,
        "workspace_path": raw_results.get('workspace_path') # Pass-through
    }

def _remove_readonly(func, path, excinfo):
    """Helper to bypass Windows filesystem permissions for Git objects."""
    import stat
    os.chmod(path, stat.S_IWRITE)
    func(path)

# --- PUBLIC INTERFACE ---

def orchestrate_scan(repo_url, cleanup=True):
    """
    Primary entry point for the Security Engine.
    Performs Cloning -> Parallel Scanning -> Normalization -> Cleanup.
    Returns: Dict (Final Unified Report)
    """
    # System Pre-check
    try:
        subprocess.run("docker version", shell=True, check=True, capture_output=True)
    except Exception:
        print("[ERROR] Docker daemon is unreachable. Scan aborted.")
        return None

    scan_id = str(uuid.uuid4())
    project_name = repo_url.split("/")[-1].replace(".git", "")
    scan_workspace = os.path.abspath(os.path.join(WORKSPACE_DIR, f"{project_name}_{scan_id}"))
    
    print(f"[SYSTEM] Starting high-level security audit for: {repo_url}")
    print(f"[SYSTEM] Internal Scan ID: {scan_id}")

    # 1. Clone
    print(f"[INFO] Cloning repository into isolated workspace...")
    try:
        result = subprocess.run(f'git clone --depth 1 {repo_url} "{scan_workspace}"', shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[ERROR] Git Clone Failed: {result.stderr.strip()}")
            return None
    except Exception as e:
        print(f"[ERROR] Failed to execute git: {e}")
        return None

    # 2. Sequential Execution (Optimized for 1GB RAM AWS/GCP Servers)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    raw_outputs = {k: os.path.join(RESULTS_DIR, f"{scan_id}_{k}.json") for k in ["opengrep", "trivy", "gitleaks", "hadolint"]}
    raw_outputs['workspace_path'] = scan_workspace # Attach for normalization pass-through
    
    _run_docker_tool("Opengrep", "opengrep scan --config auto --json", scan_workspace, raw_outputs['opengrep'])
    _run_docker_tool("Trivy", "trivy fs /src --format json", scan_workspace, raw_outputs['trivy'])
    _run_docker_tool("Gitleaks", "gitleaks detect --source=/src --report-format=json --report-path=- --no-git", scan_workspace, raw_outputs['gitleaks'])
    _run_docker_tool("Hadolint", "hadolint --format json /src/Dockerfile", scan_workspace, raw_outputs['hadolint'])

    # --- ARCHIVE: Parallel Execution (Uncomment if using Oracle Cloud 24GB RAM instance) ---
    # threads = [
    #     threading.Thread(target=_run_docker_tool, args=("Opengrep", "opengrep scan --config auto --json", scan_workspace, raw_outputs['opengrep'])),
    #     threading.Thread(target=_run_docker_tool, args=("Trivy", "trivy fs /src --format json", scan_workspace, raw_outputs['trivy'])),
    #     threading.Thread(target=_run_docker_tool, args=("Gitleaks", "gitleaks detect --source=/src --report-format=json --report-path=- --no-git", scan_workspace, raw_outputs['gitleaks'])),
    #     threading.Thread(target=_run_docker_tool, args=("Hadolint", "hadolint --format json /src/Dockerfile", scan_workspace, raw_outputs['hadolint']))
    # ]
    # for t in threads: t.start()
    # for t in threads: t.join()
    # ----------------------------------------------------------------------------------------

    # 3. Normalization
    print("[INFO] Normalizing multi-layer findings into unified schema...")
    report = _normalize_results(scan_id, raw_outputs)
    
    report_path = os.path.join(RESULTS_DIR, f"report_{project_name}_{scan_id}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"[SUCCESS] Audit complete. Found {report['total_findings']} intelligence points.")
    print(f"[INFO] Final report path: {report_path}")

    # 4. Cleanup
    if cleanup:
        print("[INFO] Purging temporary workspace...")
        try:
            shutil.rmtree(scan_workspace, onerror=_remove_readonly)
        except Exception:
            pass
    else:
        print(f"[INFO] Cleanup skipped. Workspace preserved at: {scan_workspace}")
    
    return report

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else None
    if not url:
        print("Usage: python engine.py <github_url>")
    else:
        orchestrate_scan(url)
