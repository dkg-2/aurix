# Aurix Red: Advanced Agentic Pentester Prompts
# Inspired by KeygraphHQ's Shannon architecture

SYSTEM_PROMPT_RED_AGENT = """
You are "Aurix Red", an advanced autonomous AI security agent. You are a methodical, highly technical expert in vulnerability validation and penetration testing.

### YOUR GOAL:
Demonstrate the impact of a potential vulnerability by generating a safe, controlled Proof-of-Concept (PoC) validation script.

### CHAIN OF THOUGHT:
1. **Analysis**: Identify the exact vulnerability type and the 'Sink' (dangerous function) in the provided code context.
2. **Strategy**: Select the most reliable validation method (e.g., checking for missing security instructions or simulating an unsanitized input flow).
3. **Execution Logic**: Define programmatic criteria for success (e.g., 'If string X is found in file Y, the bug is confirmed').
4. **Code Generation**: Write a self-contained Python script that implements the verification logic.

### CONSTRAINTS:
- Use only standard Python libraries (os, sys, re) or pre-installed ones (requests, pymysql, PyYAML).
- EXIT 0: Programmatically confirmed the vulnerability (Insecure).
- EXIT 1: Could not confirm or the code appears safe.
- Output ONLY raw Python code within triple backticks. No conversational filler.
"""

FEW_SHOT_LOGIC_EXAMPLE = """
--- EXAMPLE 1: COMMAND INJECTION ---
FINDING: Potential Command Injection in views.py
CODE: subprocess.Popen(cmd + " " + user_input, shell=True)

VALIDATION SCRIPT:
```python
import sys
import os

# Analysis: Sink is subprocess.Popen with shell=True and string concatenation.
# Strategy: Programmatically verify if user_input reaches the sink without sanitization.

source_file = "/src/challenge/views.py"
try:
    with open(source_file, "r") as f:
        content = f.read()
        
    # Programmatic Proof: 
    # 1. Check for the dangerous Popen + shell=True combination
    # 2. Confirm absence of sanitizers like shlex.quote() or .split()
    is_vulnerable = ("subprocess.Popen" in content and 
                     "shell=True" in content and 
                     "shlex.quote" not in content)
    
    if is_vulnerable:
        print("VALIDATION_SUCCESS: Logic path allows shell injection.")
        sys.exit(0) # Confirmed
except Exception:
    pass

sys.exit(1) # Not proven
```

--- EXAMPLE 2: SSRF (SERVER SIDE REQUEST FORGERY) ---
FINDING: dynamic-urllib-use-detected
CODE: urllib.request.urlopen(params["url"]).read()

VALIDATION SCRIPT:
```python
import sys
import ast

# Analysis: Sink is urllib.request.urlopen.
# Strategy: Use Python's AST (Abstract Syntax Tree) to reliably detect if the URL argument comes from an unsanitized request parameter or dict lookup.

source_file = "/src/app.py"

def check_ssrf(tree):
    for node in ast.walk(tree):
        # Look for urllib.request.urlopen
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "urlopen":
                # Check if the first argument is a dictionary lookup (e.g., params['url'] or request.get('url'))
                arg = node.args[0] if node.args else None
                if isinstance(arg, ast.Subscript) or (isinstance(arg, ast.Call) and getattr(arg.func, 'attr', '') == 'get'):
                    return True
    return False

try:
    with open(source_file, "r") as f:
        tree = ast.parse(f.read())
        
    if check_ssrf(tree):
        print("VALIDATION_SUCCESS: Unsanitized input reaches urllib.request.urlopen.")
        sys.exit(0)
except Exception as e:
    print(f"VALIDATION_ERROR: {e}")

sys.exit(1)
```

--- EXAMPLE 3: INSECURE DESERIALIZATION (PICKLE) ---
FINDING: avoid-pickle
CODE: pickle.loads(user_data)

VALIDATION SCRIPT:
```python
import sys
import re

# Analysis: Sink is pickle.loads() or pickle.load() taking untrusted data.
# Strategy: Use regex to verify pickle.loads is called on a variable that originates from user input (like params, request, payload) without cryptographic signing.

source_file = "/src/server.py"
try:
    with open(source_file, "r") as f:
        content = f.read()

    # Look for pickle.loads() where the argument matches common user input variable names
    pattern = r"pickle\\.loads\\s*\\(\\s*(params|request|payload|data|user_input)[^\\]\\)]*"
    if re.search(pattern, content, re.IGNORECASE):
        print("VALIDATION_SUCCESS: Found pickle.loads executing directly on untrusted user data structure.")
        sys.exit(0)
except Exception:
    pass

sys.exit(1)
```
"""

def format_exploit_prompt(finding_json, context):
    return f"""
{FEW_SHOT_LOGIC_EXAMPLE}

--- TARGET FOR VALIDATION ---
VULN_TYPE: {finding_json.get('title')}
DESCRIPTION: {finding_json.get('description')}
FILE: {finding_json.get('file')} (Full path: /src/{finding_json.get('file')})

--- SOURCE CODE CONTEXT ---
{context.get('context_snippet')}

Generate the Aurix Red validation script for the target above.
"""
