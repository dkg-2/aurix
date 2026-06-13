import operator
from typing import Annotated, List, TypedDict, Dict, Union
from langgraph.graph import StateGraph, END

# Import existing logic
from context_fetcher import ContextFetcher
from groq_client import AurixGroqClient
from sandbox_executor import SandboxExecutor
from logic_agent import SYSTEM_PROMPT_LOGIC_HYPER_BATCH, format_hyper_batch_prompt
from aurix_red_prompts import format_exploit_prompt
from blue_agent import format_patch_prompt

# --- 1. STATE DEFINITION ---
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
    retries: int # Track self-healing attempts
    last_error: str # Store sandbox stderr for the AI to read
    verified_reports: Annotated[List[Dict], operator.add] 

# --- 2. NODE IMPLEMENTATIONS ---

def pop_next_vulnerability(state: AurixState):
    vulnerabilities = state['target_vulnerabilities']
    if not vulnerabilities:
        return {"current_vuln": None}
    return {
        "current_vuln": vulnerabilities[0],
        "target_vulnerabilities": vulnerabilities[1:],
        "retries": 0,
        "last_error": None
    }

def fetch_context_node(state: AurixState):
    fetcher = ContextFetcher(state['workspace_path'])
    context = fetcher.get_finding_context(state['current_vuln']['file'], state['current_vuln']['line'])
    return {"analysis_context": context}
def logic_agent_node(state: AurixState):
    """Triage node: Is this bug real?"""
    client = AurixGroqClient()
    prompt = format_hyper_batch_prompt([(state['current_vuln'], state['analysis_context'])])
    response = client.call_logic_agent(f"{SYSTEM_PROMPT_LOGIC_HYPER_BATCH}\n\n{prompt}")

    results = response.get("results", [])
    if not results:
        # Graceful failure: if AI fails, mark as low confidence/safe to prevent crash
        return {
            "confidence_score": 0.0,
            "is_exploitable": False,
            "logic_reasoning": f"AI Triage Failed: {response.get('error', 'Unknown error')}"
        }

    result = results[0]
    return {
        "confidence_score": result.get("confidence", 0.0),
        "is_exploitable": result.get("is_exploitable", False),
        "logic_reasoning": result.get("reasoning", "No explanation.")
    }

def red_agent_node(state: AurixState):
    """The Red Agent now reads 'last_error' if it exists (Reflexion)."""
    client = AurixGroqClient()
    base_prompt = format_exploit_prompt(state['current_vuln'], state['analysis_context'])
    
    if state.get('last_error'):
        # REFLEXION LOGIC: Provide the error to the AI
        reflexion_prompt = f"{base_prompt}\n\n### REFLEXION:\nYour previous script failed with this error:\n{state['last_error']}\n\nPlease FIX the script and return ONLY the corrected Python code."
        poc = client.call_red_agent(reflexion_prompt)
    else:
        poc = client.call_red_agent(base_prompt)
        
    return {"poc_script": poc}

def blue_agent_node(state: AurixState):
    client = AurixGroqClient()
    prompt = format_patch_prompt(state['current_vuln'], state['analysis_context'], state['poc_script'])
    patch = client.call_blue_agent(prompt)
    return {"patch_code": patch}

def sandbox_node(state: AurixState):
    """Executes and captures errors for the Reflexion loop."""
    sandbox = SandboxExecutor()
    ws = state['workspace_path']
    
    # 1. First, check if the PoC even works on original code
    poc_execution = sandbox.execute_python_poc(state['poc_script'], ws, read_only=True)
    
    if not poc_execution.get("verified"):
        # PoC failed to prove the bug - return error for Reflexion
        return {
            "wargame_status": "PoC Failed",
            "last_error": poc_execution.get("stderr", "Unknown error")
        }

    # 2. If PoC worked, apply patch and verify neutralization
    sandbox.execute_python_poc(state['patch_code'], ws, read_only=False)
    wargame_exec = sandbox.execute_python_poc(state['poc_script'], ws, read_only=True)
    
    neutralized = not wargame_exec.get("verified")
    return {
        "wargame_status": "Neutralized" if neutralized else "Exploit Confirmed",
        "last_error": None if neutralized else "Patch did not stop the exploit."
    }

def save_result_node(state: AurixState):
    vuln = state['current_vuln'].copy()
    vuln.update({
        "verified": True,
        "wargame_status": state['wargame_status'],
        "ai_reasoning": state['logic_reasoning'],
        "poc_script": state['poc_script'],
        "patch_code": state['patch_code']
    })
    return {"verified_reports": [vuln]}

# --- 3. GRAPH CONSTRUCTION ---

workflow = StateGraph(AurixState)

workflow.add_node("pop_vuln", pop_next_vulnerability)
workflow.add_node("fetch_ctx", fetch_context_node)
workflow.add_node("logic_agent", logic_agent_node)
workflow.add_node("red_agent", red_agent_node)
workflow.add_node("blue_agent", blue_agent_node)
workflow.add_node("sandbox", sandbox_node)
workflow.add_node("save_result", save_result_node)

workflow.set_entry_point("pop_vuln")

# Queue Check
workflow.add_conditional_edges(
    "pop_vuln",
    lambda x: "end" if x.get("current_vuln") is None else "continue",
    {"continue": "fetch_ctx", "end": END}
)

workflow.add_edge("fetch_ctx", "logic_agent")

# Consensus Gate
workflow.add_conditional_edges(
    "logic_agent",
    lambda x: "attack" if x['is_exploitable'] and x['confidence_score'] >= 0.8 else "drop",
    {"attack": "red_agent", "drop": "pop_vuln"}
)

workflow.add_edge("red_agent", "blue_agent")
workflow.add_edge("blue_agent", "sandbox")

# --- THE REFLEXION LOOP ---
def reflexion_logic(state: AurixState):
    """Decides if we should retry, save, or drop."""
    if state['wargame_status'] == "Neutralized":
        return "save"
    
    if state['retries'] < 2: 
        print(f"    [REFLEXION] Sandbox failed. Retry {state['retries']+1}/2...")
        return "retry"
    
    return "save"

def increment_retries(state: AurixState):
    return {"retries": state['retries'] + 1}

workflow.add_node("increment_retries", increment_retries)

workflow.add_conditional_edges(
    "sandbox",
    reflexion_logic,
    {"save": "save_result", "retry": "increment_retries"}
)
workflow.add_edge("increment_retries", "red_agent")

workflow.add_edge("save_result", "pop_vuln")

aurix_engine = workflow.compile()
