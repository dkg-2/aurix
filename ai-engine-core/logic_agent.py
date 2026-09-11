# Aurix Logic Agent: Hyper-Batch Triage (Quota Optimized)

SYSTEM_PROMPT_LOGIC_HYPER_BATCH = """
You are an expert Security Researcher. You will be provided with a LIST of potential vulnerabilities found by a static scanner across an entire project.

YOUR TASK:
Analyze every finding in the context of its source code. 
Determine which are 'True Positives' (actually exploitable) and which are 'False Positives' (noisy/safe).

OUTPUT FORMAT:
You MUST return a JSON object with a 'results' key containing a list. 
Each item MUST include the 'finding_id'.

Example:
{
    "results": [
        {
            "finding_id": "javascript.lang.security.eval-detected",
            "is_exploitable": true,
            "confidence": 0.95,
            "reasoning": "User input from req.body flows directly into eval() without sanitization."
        }
    ]
}

CRITERIA:
- Mark as False Positive if: Input is hardcoded, logic is in a tutorial/test file, or input is cast to a safe type.
- Mark as True Positive if: Unsanitized user input reaches a dangerous sink (eval, sql, subprocess).
"""

def format_hyper_batch_prompt(findings_with_context):
    """
    findings_with_context: List of tuples (finding_json, context_dict)
    """
    prompt = "Below are ALL potential vulnerabilities found in this project. Triage them all in one go.\n"
    for i, (f, ctx) in enumerate(findings_with_context):
        prompt += f"\n--- FINDING #{i+1} ---\n"
        prompt += f"ID: {f.get('id')}\n"
        prompt += f"TITLE: {f.get('title')}\n"
        prompt += f"FILE: {f.get('file')}\n"
        prompt += f"CODE:\n{ctx.get('context_snippet')}\n"
    
    prompt += "\nReturn the JSON results for all findings above."
    return prompt
