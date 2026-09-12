import json
from typing import List, Tuple, Dict, Any

SYSTEM_PROMPT_TRIAGE = """You are a vulnerability triage AI. Analyze findings and source code context.
Return JSON: {"results": [{"finding_id": "<id>", "is_exploitable": <bool>, "confidence": <float>, "reasoning": "<1 sentence max>"}]}
Mark False Positive if: input is hardcoded, in test/tutorial file, cast to safe type, or behind auth.
Mark True Positive if: unsanitized user input reaches a dangerous sink.
Respond ONLY with the JSON object."""

def format_batch_prompt(findings_with_context: List[Tuple[Dict[str, Any], Dict[str, Any]]]) -> str:
    prompt = ""
    for i, (finding, context) in enumerate(findings_with_context):
        finding_id = finding.get("id", str(i))
        title = finding.get("title", "Unknown")
        file_path = finding.get("file", "unknown")
        line = finding.get("line", "0")
        
        code = context.get("context_snippet", "")
        if len(code) > 500:
            code = code[:497] + "..."
            
        prompt += f"--- Finding {i+1} ---\n"
        prompt += f"ID: {finding_id} | {title} | {file_path}:{line}\n"
        prompt += f"Code:\n{code}\n\n"
        
    prompt += "Return JSON results for all findings."
    return prompt

def estimate_batch_tokens(findings_with_context: List[Tuple[Dict[str, Any], Dict[str, Any]]]) -> int:
    sys_chars = len(SYSTEM_PROMPT_TRIAGE)
    prompt_chars = len(format_batch_prompt(findings_with_context))
    total_chars = sys_chars + prompt_chars
    return int(total_chars / 3.5)

def create_adaptive_chunks(findings_with_context: List[Tuple[Dict[str, Any], Dict[str, Any]]], max_tokens: int = 4000) -> List[List[Tuple[Dict[str, Any], Dict[str, Any]]]]:
    chunks = []
    current_chunk = []
    
    for item in findings_with_context:
        current_chunk.append(item)
        
        if estimate_batch_tokens(current_chunk) > max_tokens:
            current_chunk.pop()
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = [item]
            
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks
