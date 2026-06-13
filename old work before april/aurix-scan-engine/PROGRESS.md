# AI-Powered Unified Vulnerability Intelligence Platform — Security Engine Roadmap

**Owner:** Divyansh (Security & Scan Engine Lead)
**Status:** Implementation Phase
**Last Updated:** March 15, 2026

---

## Project Vision
A 9-layer security intelligence platform providing multi-layer vulnerability analysis (Application, Dependency, Container) with AI-powered remediation guidance and IDE heatmaps.

## Security Engine Stack
The following tools are selected for the core scanning engine:

| Layer | Tool | Focus | Status |
| :--- | :--- | :--- | :--- |
| Application (SAST) | Opengrep | Open-source code logic (SQLi, XSS, etc.) | Switched to Fork |
| Dependency (SCA) | Trivy | Library CVEs & OS vulnerabilities | Completed |
| Secrets | Gitleaks | Hardcoded secrets & API keys | Completed |
| Container (Linting) | Hadolint | Dockerfile best practices/security | Completed |

---

## Technical Roadmap

### Phase 1: Security Engine Development
- [x] Docker Isolation Strategy: Design the "Worker" container that will pull and scan untrusted code. (Completed)
- [x] Tool Integration: (Completed)
    - [x] Configure Opengrep for core application vulnerability types.
    - [x] Configure Trivy for SCA and Container scans.
    - [x] Integrate Gitleaks for secrets detection.
    - [x] Integrate Hadolint for Dockerfile analysis.
- [x] Normalization Layer: (Completed)
    - [x] Analyze raw JSON outputs from all tools.
    - [x] Define the Unified JSON Schema (The Contract).
    - [x] Write the Converter Script (Python).

### Phase 2: Orchestration & Data Flow
- [x] Master Orchestrator: Create engine.py to automate URL -> Scan -> JSON workflow. (Completed)
- [x] Multi-Language Support: Verified engine against Node.js and Python repositories. (Completed)
- [x] Repository Deployment: Successfully pushed work to GitHub branch 'DG'. (Completed)
- [ ] Redis Job Queue Integration: To be coordinated with Platform Lead.
- [ ] Error handling for high-volume concurrent scans.

---

## Key Decisions & Progress Log

### 2026-03-14: Toolset Expansion
- Decision: Added Gitleaks and Hadolint to the engine.
- Rationale: Semgrep and Trivy are excellent, but Gitleaks provides superior secret detection (including git history), and Hadolint ensures container best practices are followed.

### 2026-03-15: Normalization and Automation
- Action: Implemented V4 of the normalization logic with Heuristic Risk Scoring.
- Action: Developed engine.py for full end-to-end automation of the scanning lifecycle.
- Deployment: Pushed all code and documentation to the Major-Project repository under the 'DG' branch.
