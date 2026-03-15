# AI-Powered Unified Vulnerability Intelligence Platform — Security Engine

## Overview
The Security Engine is the core analytical component of the platform. It is responsible for ingesting source code from GitHub repositories, executing multi-layer security scans in isolated environments, and normalizing diverse tool outputs into a single, actionable intelligence report.

This component handles the "Heavy Lifting" of the project, ensuring that untrusted code is scanned safely without risking the host system.

## Core Features
- **Multi-Layer Analysis:** Simultaneous scanning of Application (SAST), Dependency (SCA), Secrets, and Infrastructure (Dockerfile) layers.
- **Docker Isolation:** Every scan runs inside a ephemeral, hardened container to prevent side-effects on the host machine.
- **Unified Schema:** Converts disparate JSON formats from industry-standard tools into a consistent "Intelligence Schema" used by the Risk Modeling and AI components.
- **Language Agnostic:** Tested and verified on Node.js, Python, and multi-framework repositories.
- **Parallel Execution:** Uses Python multi-threading to run security tools concurrently, reducing scan time by up to 70%.

## Architecture
The engine follows a "Black Box" design:
1. **Trigger:** Receives a GitHub URL via the `orchestrate_scan()` interface.
2. **Setup:** Clones the repository into a unique, temporary workspace.
3. **Execution:** Dispatches parallel Docker containers for:
   - **Opengrep:** Finding logical vulnerabilities (SQLi, XSS).
   - **Trivy:** Detecting vulnerable third-party packages.
   - **Gitleaks:** Scanning for hardcoded credentials.
   - **Hadolint:** Verifying Dockerfile security best practices.
4. **Normalization:** Aggregates raw outputs and maps them to standard CVSS/Severity levels.
5. **Output:** Generates a single, time-stamped JSON report.
6. **Cleanup:** Purges temporary source code to maintain system integrity.

## Quick Start for Team Members
### 1. Prerequisites
- Docker Desktop (Running)
- Python 3.11+

### 2. Build the Engine
From the project root, build the core image:
```bash
docker build -t security-engine:latest -f security-engine.Dockerfile .
```

### 3. Run a Test Scan
```bash
python engine.py https://github.com/OWASP/NodeGoat.git
```

## Team Integration Contracts
- **For Platform Lead (Bhavya):** See `README_ENGINE.md` for programmatic integration details.
- **For Risk Lead (Bhumika):** The engine provides standardized `cvss` (float) and `severity` (string) for all findings.
- **For AI Lead (Divyanshi):** The engine provides `evidence` (code snippets) and `fix` suggestions for LLM processing.
