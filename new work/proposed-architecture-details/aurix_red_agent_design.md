# Aurix Red: Autonomous Agentic Pentester Design

This document outlines the from-scratch implementation plan for **Aurix Red**, the specialized "Red Team Agent" within the Project AURIX LangGraph orchestrator. This design is heavily inspired by the "No Exploit, No Report" philosophy of state-of-the-art tools like KeygraphHQ's Shannon.

## 1. Core Philosophy: "No Exploit, No Report"
Currently, our Scan Engine (Opengrep, Trivy) produces hundreds of potential vulnerabilities (the `total_findings`). Aurix Red's job is **not to find more bugs**, but to **prove that existing bugs are real**. 
If Aurix Red cannot write a functional Python/Bash script (Proof-of-Concept) that successfully exploits the finding in a sandbox, the vulnerability is marked as a "False Positive" and hidden from the developer.

## 2. Architecture & Execution Loop (LangGraph Integration)

Aurix Red will be implemented as a specialized node in our LangGraph state machine.

### Phase A: Context Ingestion (The "Hypothesis")
When the **Logic Agent** flags a SAST finding (e.g., a SQL Injection in `views.py`) with a confidence score > 0.80, the state is passed to Aurix Red.
*   **Input State:** 
    *   `vuln_type`: "SQL Injection"
    *   `file_path`: "introduction/views.py"
    *   `line_number`: 158
    *   `code_snippet`: `sql_query = "SELECT * FROM users WHERE user='"+name+"' AND password='"+password+"'"`

### Phase B: PoC Generation (The "Weaponization")
Aurix Red (powered by an LLM like GPT-4 or Claude 3) is prompted to act as a Senior Penetration Tester.
*   **Task:** Write a standalone Python script (`exploit.py`) using the `requests` library that attempts to exploit the specific `code_snippet` at the target application's local URL (e.g., `http://localhost:8000`).
*   **Constraint:** The script must exit with code `0` if the exploit succeeds (e.g., it successfully bypassed login) and exit with code `1` if it fails.

### Phase C: The Ephemeral Sandbox (The "Execution")
This is the most critical and dangerous part. We cannot run LLM-generated malware directly on the Worker Node.
1.  **Spin-up:** The Worker Node uses the `docker` SDK to spin up a lightweight, network-isolated container (`python:3.11-slim`).
2.  **Mount:** The `exploit.py` script is mounted into the container.
3.  **Execute:** The container runs `python exploit.py`.
4.  **Evaluate:** Aurix Red captures the `exit_code` and `stdout`.

### Phase D: State Update (The "Verdict")
*   **If Exit Code == 0:** Aurix Red updates the LangGraph state: `wargame_status = "Exploit Verified"`. The `poc_script` is attached to the final report so the developer can run it themselves.
*   **If Exit Code != 0:** The agent gets **one retry** to fix its exploit script based on the `stderr`. If it fails again, `wargame_status = "Unverifiable / False Positive"`.

## 3. Implementation Steps for Aurix (From Scratch)

To build this, we need to implement the following Python components in our `new work` directory:

1.  **`aurix_red_prompts.py`:** 
    *   System prompts defining the "Attacker Persona."
    *   Few-shot examples of translating Opengrep JSON into Python `requests` exploits.
2.  **`sandbox_executor.py`:**
    *   A Python module using the `docker` library to dynamically create a container, run a string of Python code, capture the exit code, and immediately destroy the container.
3.  **`langgraph_red_node.py`:**
    *   The actual LangGraph node function that ties the prompt, the LLM call, and the sandbox executor together, updating the `AurixState`.

## 4. Why This Beats the Market
Most open-source wrappers just dump Semgrep results into a dashboard. By implementing the Aurix Red sandbox loop, we guarantee **Zero False Positives**. Developers only see bugs that have an attached, playable "Hack Button" (the PoC script), forcing them to take the issue seriously.
