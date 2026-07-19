# Project AURIX: Future Improvements & Roadmap

As AURIX continues to mature, this document tracks planned enhancements and integrations that will expand the platform's capabilities without compromising on performance or architecture.

---

## 1. Data Security & Privacy Scanning (Bearer CLI)

**Status:** Planned for Future Release
**Category:** Scan Engine (Phase 1) Enhancement

### The Objective
Currently, the AURIX scan engine (Opengrep, Trivy, Gitleaks, Hadolint) is highly effective at finding standard OWASP vulnerabilities, misconfigurations, and hardcoded secrets. However, to increase the platform's enterprise credibility, we plan to introduce deep **Data Flow and Privacy (PII) Analysis**.

### The Tool: Bearer CLI
We will integrate [Bearer](https://github.com/Bearer/bearer), an open-source, lightning-fast SAST tool specifically designed for data security. 

Unlike Opengrep (which uses pattern matching), Bearer uses **inter-procedural data flow analysis** (taint tracking). It maps where sensitive data (like Credit Cards, SSNs, Passwords) enters the application and traces its execution path. If the sensitive data flows into an unsafe "sink" (e.g., printed to `console.log()` or sent over unencrypted HTTP), Bearer flags it.

**Why Bearer?**
- **Zero Overlap:** It covers a completely different vulnerability class (Data Privacy / Compliance) than our existing tools, meaning no duplicate findings.
- **High Performance:** Compiled in Go, it runs in seconds and is designed specifically for CI/CD pipelines.

### Implementation Steps

When the team is ready to build this, follow these steps:

1. **Update the Engine Dockerfile (`sandbox/Dockerfile` or Engine Image):**
   Add the installation script for the Bearer binary.
   ```dockerfile
   RUN curl -sfL https://raw.githubusercontent.com/Bearer/bearer/main/contrib/install.sh | sh
   ```

2. **Update `engine.py`:**
   Add a new parallel execution thread alongside Opengrep and Trivy. The shell execution command will be:
   ```bash
   bearer scan /workspace_path --format json --output bearer-report.json
   ```

3. **Normalize the Output:**
   Create a new parser function in `engine.py` that reads `bearer-report.json`. Bearer's JSON output is highly structured (providing `file`, `line`, `title`, and `snippet`). Map these fields into the AURIX "Unified Intelligence Schema" and append them to the `target_vulnerabilities` array so Divyansh's LangGraph AI can reason about them.

---

## 2. "Self-Critique" Syntax Review Node (LangGraph)

**Status:** Planned for Future Release
**Category:** LangGraph Orchestrator (Phase 3) Enhancement

### The Objective
Currently, the Reflexion loop waits for the Docker sandbox to crash before it tries to fix a broken exploit script. This wastes precious API wait times and Docker spin-up cycles. We need to catch basic hallucinations *before* execution.

### Implementation Steps
1. Add a fast `Syntax Reviewer` node to `aurix_graph.py` right after the Red Agent and Blue Agent generate code, but *before* the Sandbox node. 
2. Use the smaller, faster `gpt-oss-20b` (or similar fast model) to quickly read the generated script and check for obvious Python syntax errors, missing imports, or undefined variables.
3. Add a conditional edge: If the fast model detects a syntax error, route it back to the Red/Blue agent immediately. If it looks structurally sound, proceed to the Sandbox.

---

## 3. Multi-Model Fallback System (LangGraph)

**Status:** Planned for Future Release
**Category:** LangGraph Orchestrator (Phase 3) Enhancement

### The Objective
Open-source models (like the 120b model currently used) are highly cost-effective but can sometimes get stuck in logic loops on the hardest vulnerabilities (e.g., complex SSRF or advanced Deserialization). We need a safety net to boost our neutralization success rate.

### Implementation Steps
1. Modify the Reflexion Loop in `aurix_graph.py`. 
2. Track the number of failed retries for a specific vulnerability in the `AurixState`.
3. If the primary OSS model fails twice in the sandbox, trigger a conditional edge to fall back to a frontier commercial model (like GPT-4o, Gemini 1.5 Pro, or Claude 3.5 Sonnet) for the 3rd and final attempt. This keeps costs near zero for 90% of bugs, but uses heavy hitters to rescue the hardest 10%.
