# Unified Vulnerability Intelligence — Security Engine

This module provides the core scanning and normalization capabilities for the platform. It is designed to be language-agnostic and executes multiple security engines in parallel using isolated Docker containers.

## Integrated Engines
- **Opengrep:** Application Layer (SAST)
- **Trivy:** Dependency Layer (SCA)
- **Gitleaks:** Secret Detection Layer
- **Hadolint:** Infrastructure/Dockerfile Layer

## Integration Guide (For Platform & Backend Lead)

The engine is designed as a "Black Box" module. You can trigger it from your Node.js backend using a child process or by importing it into a Python-based Redis worker.

### Standard Execution (CLI)
```bash
python engine.py <github_repo_url>
```

### Programmatic Integration (Python)
```python
from engine import orchestrate_scan

# Returns a dictionary containing the full normalized report
report = orchestrate_scan("https://github.com/OWASP/NodeGoat.git")

print(report['scan_id'])
print(f"Total Issues: {report['total_findings']}")
```

## Unified intelligence Schema
Every finding returned by the engine follows this strict schema to ensure compatibility with the Risk Engine and AI Security Agent:

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | String | Unique identifier for the vulnerability (e.g., CVE-XXX or Rule-ID) |
| `tool` | String | The source tool (`opengrep`, `trivy`, `gitleaks`, `hadolint`) |
| `category` | String | High-level layer (`sast`, `sca`, `secrets`, `infra`) |
| `title` | String | Concise title of the security issue |
| `description` | String | Detailed technical explanation |
| `severity` | String | Standardized level: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO` |
| `cvss` | Float | 0.0 - 10.0 risk score (uses tool data or heuristic fallback) |
| `file` | String | Path to the affected file |
| `line` | Integer | Line number (0 if file-wide) |
| `evidence` | String | The raw code snippet or package name causing the issue |
| `fix` | String | Remediation guidance |
| `references` | Array | List of URLs for further reading/CVE details |

## Requirements
- **Docker Desktop:** Must be running and accessible to the user executing the script.
- **Image:** `security-engine:latest` must be built (see `security-engine.Dockerfile`).
- **Python 3.11+**
