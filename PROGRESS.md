# AI-Powered Unified Vulnerability Intelligence Platform — Security Engine Roadmap

**Owner:** Divyansh (Security & Scan Engine Lead)
**Status:** Research & Architecture Phase
**Last Updated:** March 14, 2026

---

## 🎯 Project Vision
A 9-layer security intelligence platform providing multi-layer vulnerability analysis (Application, Dependency, Container) with AI-powered remediation guidance and IDE heatmaps.

## 🛠️ Security Engine Stack
The following tools are selected for the core scanning engine:

| Layer | Tool | Focus | Status |
| :--- | :--- | :--- | :--- |
| **Application (SAST)** | **Opengrep** | Open-source code logic (SQLi, XSS, etc.) | ✅ Switched to Fork |
| **Dependency (SCA)** | **Trivy** | Library CVEs & OS vulnerabilities | 📝 Planned |
| **Secrets** | **Gitleaks** | Hardcoded secrets & API keys | ✅ Added to Plan |
| **Container (Linting)** | **Hadolint** | Dockerfile best practices/security | ✅ Added to Plan |

---

## 🏗️ Technical Roadmap

### Phase 1: Security Engine Development (Current)
- [x] **Docker Isolation Strategy:** Design the "Worker" container that will pull and scan untrusted code. ✅ Done
- [x] **Tool Integration:** ✅ Done
    - [x] Configure Opengrep for core 8 application vulnerability types.
    - [x] Configure Trivy for SCA and Container scans.
    - [x] Integrate Gitleaks for secrets detection.
    - [x] Integrate Hadolint for Dockerfile analysis.
- [x] **Normalization Layer:** ✅ Done
    - [x] Analyze raw JSON outputs from all 4 tools.
    - [x] Define the **Unified JSON Schema** (The Contract).
    - [x] Write the **Converter Script** (Python/Node.js). ✅ Done

### Phase 2: Orchestration & Data Flow (Current)
- [x] **Master Orchestrator:** Create `engine.py` to automate URL -> Scan -> JSON workflow. ✅ Done
- [ ] Connect Security Engine to the **Redis Job Queue**.
- [ ] Ensure seamless data handoff to the **Risk & Heat Modeling Engine** (Bhumika's layer).
- [ ] Implement error handling for failed scans or timeout issues.

---

## 📓 Key Decisions & Progress Log

### 2026-03-14: Toolset Expansion
- **Decision:** Added **Gitleaks** and **Hadolint** to the engine.
- **Rationale:** Semgrep and Trivy are excellent, but Gitleaks provides superior secret detection (including git history), and Hadolint ensures container best practices are followed from the start.
- **Action:** Updated project roadmap to include these tools in the Normalization Layer.
