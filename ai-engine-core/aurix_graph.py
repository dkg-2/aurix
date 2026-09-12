"""
AURIX LangGraph Engine v2 — Optimized State Machine for Vulnerability Validation.

Architecture:
  pop_vuln → fetch_ctx → triage_gate → red_agent → blue_agent → sandbox → reflexion → save → loop

Optimizations over v1:
  - Triage gate skips API call if finding was pre-triaged by the Hyper-Batch worker
  - Red/Blue agents use compressed prompts
  - Reflexion loop capped at 2 retries with clear error feedback
  - All API calls go through the token-aware AurixGroqClient
"""

import operator
from typing import Annotated, List, TypedDict, Dict
from langgraph.graph import StateGraph, END

from context_fetcher import ContextFetcher
from groq_client import call_triage, call_reasoning
from sandbox_executor import SandboxExecutor
from aurix_red_prompts import format_exploit_prompt
from blue_agent import format_patch_prompt


# ═══════════════════════════════════════════════
# 1. STATE SCHEMA
# ═══════════════════════════════════════════════

class AurixState(TypedDict):
    workspace_path: str
    target_vulnerabilities: List[Dict]
    current_vuln: Dict
    analysis_context: Dict
    confidence_score: float
    is_exploitable: bool
    logic_reasoning: str
    poc_script: str
    patch_code: str
    wargame_status: str
    retries: int
    last_error: str
    verified_reports: Annotated[List[Dict], operator.add]


# ═══════════════════════════════════════════════
# 2. NODE IMPLEMENTATIONS
# ═══════════════════════════════════════════════

def pop_next_vulnerability(state: AurixState):
    """Pops the next vulnerability from the queue. Returns None when empty."""
    vulns = state['target_vulnerabilities']
    if not vulns:
        return {"current_vuln": None}
    
    vuln = vulns[0]
    remaining = vulns[1:]
    print(f"    [GRAPH] Processing: {vuln.get('title', 'Unknown')} ({len(remaining)} remaining)")
    
    return {
        "current_vuln": vuln,
        "target_vulnerabilities": remaining,
        "retries": 0,
        "last_error": None
    }


def fetch_context_node(state: AurixState):
    """Fetches source code context for the current vulnerability using AST slicing."""
    vuln = state['current_vuln']
    
    # If context was already fetched during triage, reuse it
    if vuln.get('_context'):
        return {"analysis_context": vuln['_context']}
    
    fetcher = ContextFetcher(state['workspace_path'])
    context = fetcher.get_finding_context(vuln['file'], vuln['line'])
    return {"analysis_context": context}


def triage_gate_node(state: AurixState):
    """
    Triage gate: Uses pre-computed triage data from the worker's batch step.
    Only falls back to a live API call if the finding wasn't pre-triaged.
    """
    vuln = state['current_vuln']
    
    # Fast path: already triaged by the worker
    if vuln.get('_triage_reasoning'):
        return {
            "confidence_score": 1.0,
            "is_exploitable": True,
            "logic_reasoning": vuln['_triage_reasoning']
        }
    
    # Slow path: live triage (shouldn't normally happen)
    prompt = f"""Analyze this vulnerability and determine if it is exploitable.
Title: {vuln.get('title')}
File: {vuln.get('file')}
Code: {state.get('analysis_context', {}).get('context_snippet', 'N/A')}

Return JSON: {{"is_exploitable": bool, "confidence": float, "reasoning": "one sentence"}}"""
    
    response = call_triage(prompt)
    return {
        "confidence_score": response.get("confidence", 0.0),
        "is_exploitable": response.get("is_exploitable", False),
        "logic_reasoning": response.get("reasoning", "Live triage fallback.")
    }


def red_agent_node(state: AurixState):
    """Red Agent: Generates a Proof-of-Concept exploit script with Reflexion support."""
    base_prompt = format_exploit_prompt(state['current_vuln'], state['analysis_context'])
    
    if state.get('last_error'):
        prompt = (
            f"{base_prompt}\n\n"
            f"### REFLEXION:\n"
            f"Your previous script failed with this error:\n{state['last_error']}\n"
            f"Fix the script. Return ONLY corrected Python code."
        )
    else:
        prompt = base_prompt
    
    poc = call_reasoning(prompt)
    return {"poc_script": poc}


def blue_agent_node(state: AurixState):
    """Blue Agent: Generates a patch script to remediate the vulnerability."""
    prompt = format_patch_prompt(state['current_vuln'], state['analysis_context'], state['poc_script'])
    patch = call_reasoning(prompt)
    return {"patch_code": patch}


def sandbox_node(state: AurixState):
    """
    Sandbox: Executes the PoC in a Docker container, then applies the patch
    and re-runs the PoC to verify neutralization.
    """
    sandbox = SandboxExecutor()
    ws = state['workspace_path']
    
    # Step 1: Verify the PoC proves the vulnerability on original code
    poc_result = sandbox.execute_python_poc(state['poc_script'], ws, read_only=True)
    
    if not poc_result.get("verified"):
        error_msg = poc_result.get("stderr") or poc_result.get("error") or "PoC did not confirm the vulnerability"
        return {
            "wargame_status": "PoC Failed",
            "last_error": error_msg[:500]  # Truncate to save tokens on Reflexion
        }
    
    # Step 2: Apply patch (read-write mode)
    sandbox.execute_python_poc(state['patch_code'], ws, read_only=False)
    
    # Step 3: Re-run PoC to verify the patch neutralized the vulnerability
    post_patch = sandbox.execute_python_poc(state['poc_script'], ws, read_only=True)
    
    neutralized = not post_patch.get("verified")
    return {
        "wargame_status": "Neutralized" if neutralized else "Exploit Confirmed",
        "last_error": None if neutralized else "Patch did not stop the exploit."
    }


def save_result_node(state: AurixState):
    """Saves the verified vulnerability report to the results list."""
    vuln = state['current_vuln'].copy()
    
    # Clean up internal fields before saving
    vuln.pop('_triage_reasoning', None)
    vuln.pop('_context', None)
    
    vuln.update({
        "verified": True,
        "wargame_status": state['wargame_status'],
        "ai_reasoning": state['logic_reasoning'],
        "poc_script": state['poc_script'],
        "patch_code": state['patch_code']
    })
    
    status_icon = "✅" if state['wargame_status'] == "Neutralized" else "⚠️"
    print(f"    [GRAPH] {status_icon} {vuln.get('title')}: {state['wargame_status']}")
    
    return {"verified_reports": [vuln]}


def increment_retries(state: AurixState):
    """Bumps the retry counter for the Reflexion loop."""
    return {"retries": state['retries'] + 1}


# ═══════════════════════════════════════════════
# 3. ROUTING LOGIC
# ═══════════════════════════════════════════════

def queue_check(state: AurixState):
    """Routes to 'end' if no more vulnerabilities, else 'continue'."""
    return "end" if state.get("current_vuln") is None else "continue"

def triage_check(state: AurixState):
    """Routes to 'attack' if exploitable with high confidence, else 'drop'."""
    if state['is_exploitable'] and state['confidence_score'] >= 0.7:
        return "attack"
    return "drop"

def reflexion_check(state: AurixState):
    """Routes to 'save' if neutralized or retries exhausted, else 'retry'."""
    if state['wargame_status'] == "Neutralized":
        return "save"
    if state['retries'] < 2:
        print(f"    [REFLEXION] Retry {state['retries'] + 1}/2: {state.get('last_error', '')[:100]}")
        return "retry"
    return "save"


# ═══════════════════════════════════════════════
# 4. GRAPH CONSTRUCTION
# ═══════════════════════════════════════════════

workflow = StateGraph(AurixState)

# Register all nodes
workflow.add_node("pop_vuln", pop_next_vulnerability)
workflow.add_node("fetch_ctx", fetch_context_node)
workflow.add_node("triage_gate", triage_gate_node)
workflow.add_node("red_agent", red_agent_node)
workflow.add_node("blue_agent", blue_agent_node)
workflow.add_node("sandbox", sandbox_node)
workflow.add_node("save_result", save_result_node)
workflow.add_node("increment_retries", increment_retries)

# Set entry point
workflow.set_entry_point("pop_vuln")

# Edges
workflow.add_conditional_edges("pop_vuln", queue_check, {"continue": "fetch_ctx", "end": END})
workflow.add_edge("fetch_ctx", "triage_gate")
workflow.add_conditional_edges("triage_gate", triage_check, {"attack": "red_agent", "drop": "pop_vuln"})
workflow.add_edge("red_agent", "blue_agent")
workflow.add_edge("blue_agent", "sandbox")
workflow.add_conditional_edges("sandbox", reflexion_check, {"save": "save_result", "retry": "increment_retries"})
workflow.add_edge("increment_retries", "red_agent")
workflow.add_edge("save_result", "pop_vuln")

# Compile the engine
aurix_engine = workflow.compile()
