# Aurix Blue Agent: Autonomous Remediation & Patching

SYSTEM_PROMPT_BLUE_AGENT = """
You are "Aurix Blue", an advanced autonomous AI security engineer. Your goal is to remediate vulnerabilities confirmed by the Red Agent.

### YOUR TASK:
1. **Analyze the Proof**: Review the source code context and the Proof-of-Concept (PoC) script that successfully exploited the vulnerability.
2. **Generate a Patch**: Provide a surgical code fix that eliminates the vulnerability.
3. **Preserve Functionality**: Ensure the fix does not break the original logic or change the coding style.

### CONSTRAINTS:
- Use standard secure coding practices (e.g., parameterized queries, input sanitization, non-root users).
- Provide the fix as a Python 'Patch Script' that uses standard file operations to modify the target file.
- Output ONLY raw Python code within triple backticks.
"""

FEW_SHOT_FIX_EXAMPLE = """
--- EXAMPLE 1: SQL INJECTION (SQLAlchemy) ---
FINDING: SQL Injection in core/db.js
POC: Proved that concatenating 'id' allows logic bypass.

BLUE PATCH SCRIPT:
```python
import os

target_file = "/src/core/db.js"
with open(target_file, "r") as f:
    content = f.read()

# Surgical replacement: Replace concatenation with parameterized query
old_code = 'cursor.execute("SELECT * FROM users WHERE id=" + params["id"])'
new_code = 'cursor.execute("SELECT * FROM users WHERE id=%s", (params["id"],))'

if old_code in content:
    new_content = content.replace(old_code, new_code)
    with open(target_file, "w") as f:
        f.write(new_content)
    print("PATCH_APPLIED: SQL Injection mitigated.")
```

--- EXAMPLE 2: SSRF (urllib) ---
FINDING: dynamic-urllib-use-detected
POC: Proved arbitrary file read via file:// scheme in urlopen.

BLUE PATCH SCRIPT:
```python
import os
import re

target_file = "/src/app.py"
with open(target_file, "r") as f:
    content = f.read()

# Surgical replacement: Inject a safe wrapper and replace the unsafe call
safe_wrapper = '''
def safe_urlopen(url):
    from urllib.parse import urlparse
    if urlparse(url).scheme not in ("http", "https"):
        raise ValueError("Unsupported scheme")
    import urllib.request
    return urllib.request.urlopen(url)
'''

# Find last import and inject wrapper
imports = list(re.finditer(r'^(import .+|from .+ import .+)$', content, re.MULTILINE))
if imports:
    insert_pos = imports[-1].end()
    content = content[:insert_pos] + "\\n" + safe_wrapper + content[insert_pos:]

# Replace the unsafe call
content = content.replace("urllib.request.urlopen(params['url'])", "safe_urlopen(params['url'])")

with open(target_file, "w") as f:
    f.write(content)
print("PATCH_APPLIED: SSRF mitigated via safe_urlopen wrapper.")
```
"""

def format_patch_prompt(finding_json, context, poc_script):
    return f"""
{FEW_SHOT_FIX_EXAMPLE}

--- VULNERABILITY TO FIX ---
TITLE: {finding_json.get('title')}
FILE: {finding_json.get('file')}
REASONING: {finding_json.get('ai_reasoning')}

--- PROOF OF CONCEPT (PoC) ---
{poc_script}

--- ORIGINAL CODE CONTEXT ---
{context.get('context_snippet')}

Generate the Aurix Blue patch script to secure the file at /src/{finding_json.get('file')}.
"""
