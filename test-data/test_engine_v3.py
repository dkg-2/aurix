"""
AURIX Engine v3 — Local Validation Test
Tests every component individually to ensure the rewrite works before deployment.
"""

import sys
import os

# Add the engine directory to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai-engine-core"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "ai-engine-core", ".env"))

PASS = "[PASS]"
FAIL = "[FAIL]"
results = []

def test(name, func):
    try:
        func()
        print(f"  {PASS} {name}")
        results.append((name, True))
    except Exception as e:
        print(f"  {FAIL} {name}: {e}")
        results.append((name, False))


# ═══════════════════════════════════════════════
# TEST 1: Import Validation
# ═══════════════════════════════════════════════
print("\n" + "="*60)
print("TEST 1: Import Validation")
print("="*60)

def test_import_groq_client():
    from groq_client import call_triage, call_reasoning, estimate_tokens
    assert callable(call_triage)
    assert callable(call_reasoning)
    assert callable(estimate_tokens)

def test_import_logic_agent():
    from logic_agent import SYSTEM_PROMPT_TRIAGE, format_batch_prompt, create_adaptive_chunks
    assert SYSTEM_PROMPT_TRIAGE is not None
    assert callable(format_batch_prompt)
    assert callable(create_adaptive_chunks)

def test_import_graph():
    from aurix_graph import aurix_engine
    assert aurix_engine is not None

def test_import_worker():
    from aurix_worker import AurixWorker
    assert AurixWorker is not None

def test_import_context_fetcher():
    from context_fetcher import ContextFetcher
    assert ContextFetcher is not None

test("Import groq_client", test_import_groq_client)
test("Import logic_agent", test_import_logic_agent)
test("Import aurix_graph", test_import_graph)
test("Import aurix_worker", test_import_worker)
test("Import context_fetcher", test_import_context_fetcher)


# ═══════════════════════════════════════════════
# TEST 2: Token Estimation
# ═══════════════════════════════════════════════
print("\n" + "="*60)
print("TEST 2: Token Estimation")
print("="*60)

def test_token_estimation():
    from groq_client import estimate_tokens
    # ~3.5 chars per token
    tokens = estimate_tokens("Hello world, this is a test string")
    assert 5 < tokens < 20, f"Expected 5-20 tokens, got {tokens}"
    
    # Empty string
    assert estimate_tokens("") >= 0

def test_token_long_text():
    from groq_client import estimate_tokens
    text = "x" * 35000  # ~10,000 tokens
    tokens = estimate_tokens(text)
    assert 9000 < tokens < 11000, f"Expected ~10000 tokens, got {tokens}"

test("Token estimation (short text)", test_token_estimation)
test("Token estimation (long text)", test_token_long_text)


# ═══════════════════════════════════════════════
# TEST 3: Adaptive Chunking (Bin Packing)
# ═══════════════════════════════════════════════
print("\n" + "="*60)
print("TEST 3: Adaptive Chunking")
print("="*60)

def test_adaptive_chunking_basic():
    from logic_agent import create_adaptive_chunks
    
    # Create 10 mock findings with context
    mock_findings = []
    for i in range(10):
        finding = {"id": f"vuln-{i}", "title": f"SQL Injection #{i}", "file": f"app.py", "line": i*10}
        context = {"context_snippet": f"cursor.execute('SELECT * FROM users WHERE id=' + request.args['id'])  # line {i}"}
        mock_findings.append((finding, context))
    
    chunks = create_adaptive_chunks(mock_findings, max_tokens=5500)
    
    # Should produce at least 1 chunk
    assert len(chunks) >= 1, f"Expected at least 1 chunk, got {len(chunks)}"
    
    # All findings should be accounted for
    total = sum(len(c) for c in chunks)
    assert total == 10, f"Expected 10 total findings across chunks, got {total}"
    
    print(f"    -> {len(mock_findings)} findings split into {len(chunks)} chunks")

def test_adaptive_chunking_large():
    from logic_agent import create_adaptive_chunks
    
    # Create 50 findings with large context (simulating a big repo)
    mock_findings = []
    for i in range(50):
        finding = {"id": f"vuln-{i}", "title": f"XSS Vulnerability #{i}", "file": f"views/page{i}.py", "line": i*5}
        context = {"context_snippet": "def handle_request(request):\n    user_input = request.GET.get('q')\n    return HttpResponse(f'<h1>{user_input}</h1>')  # XSS!\n" * 3}
        mock_findings.append((finding, context))
    
    chunks = create_adaptive_chunks(mock_findings, max_tokens=5500)
    
    total = sum(len(c) for c in chunks)
    assert total == 50, f"Expected 50 findings, got {total}"
    
    print(f"    -> {len(mock_findings)} large findings split into {len(chunks)} chunks")

def test_adaptive_chunking_single_huge():
    from logic_agent import create_adaptive_chunks
    
    # Single finding with massive context — should be its own chunk
    finding = {"id": "huge-1", "title": "Massive Finding", "file": "big.py", "line": 1}
    context = {"context_snippet": "x = 1\n" * 500}  # Very large
    
    chunks = create_adaptive_chunks([(finding, context)], max_tokens=5500)
    assert len(chunks) == 1
    assert len(chunks[0]) == 1

test("Adaptive chunking (10 findings)", test_adaptive_chunking_basic)
test("Adaptive chunking (50 large findings)", test_adaptive_chunking_large)
test("Adaptive chunking (1 huge finding)", test_adaptive_chunking_single_huge)


# ═══════════════════════════════════════════════
# TEST 4: Prompt Formatting
# ═══════════════════════════════════════════════
print("\n" + "="*60)
print("TEST 4: Prompt Formatting")
print("="*60)

def test_batch_prompt_format():
    from logic_agent import format_batch_prompt, SYSTEM_PROMPT_TRIAGE
    from groq_client import estimate_tokens
    
    findings = [
        ({"id": "sql-1", "title": "SQL Injection", "file": "db.py", "line": 42},
         {"context_snippet": "cursor.execute('SELECT * FROM users WHERE id=' + uid)"}),
        ({"id": "xss-1", "title": "XSS", "file": "views.py", "line": 15},
         {"context_snippet": "return f'<div>{user_input}</div>'"})
    ]
    
    prompt = format_batch_prompt(findings)
    full = SYSTEM_PROMPT_TRIAGE + "\n\n" + prompt
    tokens = estimate_tokens(full)
    
    assert "sql-1" in prompt
    assert "xss-1" in prompt
    assert tokens < 5500, f"Prompt uses {tokens} tokens (limit: 5500)"
    
    print(f"    -> 2-finding prompt uses ~{tokens} tokens")

def test_system_prompt_size():
    from logic_agent import SYSTEM_PROMPT_TRIAGE
    from groq_client import estimate_tokens
    
    tokens = estimate_tokens(SYSTEM_PROMPT_TRIAGE)
    assert tokens < 300, f"System prompt is {tokens} tokens (limit: 300)"
    print(f"    -> System prompt: ~{tokens} tokens")

test("Batch prompt format", test_batch_prompt_format)
test("System prompt size", test_system_prompt_size)


# ═══════════════════════════════════════════════
# TEST 5: Live Groq API Call
# ═══════════════════════════════════════════════
print("\n" + "="*60)
print("TEST 5: Live Groq API Call (requires GROQ_API_KEY)")
print("="*60)

def test_live_triage():
    from groq_client import call_triage
    
    prompt = """You are a vulnerability triage AI. Analyze this finding:
--- Finding 1 ---
ID: test-sqli | SQL Injection | app.py:10
Code:
cursor.execute("SELECT * FROM users WHERE id=" + request.args['id'])

Return JSON: {"results": [{"finding_id": "test-sqli", "is_exploitable": true, "confidence": 0.95, "reasoning": "one sentence"}]}"""
    
    response = call_triage(prompt)
    
    assert isinstance(response, dict), f"Expected dict, got {type(response)}"
    assert "results" in response, f"Response missing 'results' key: {response}"
    assert len(response["results"]) > 0, "No results returned"
    
    r = response["results"][0]
    print(f"    -> finding_id: {r.get('finding_id')}")
    print(f"    -> is_exploitable: {r.get('is_exploitable')}")
    print(f"    -> confidence: {r.get('confidence')}")
    print(f"    -> reasoning: {r.get('reasoning')}")

def test_live_reasoning():
    from groq_client import call_reasoning
    
    prompt = """Generate a simple Python script that checks if a file contains the string 'eval(' in it.
Output ONLY Python code in ```python``` blocks."""
    
    response = call_reasoning(prompt)
    
    assert len(response) > 10, f"Response too short: {response[:50]}"
    assert "eval" in response.lower(), "Response doesn't contain 'eval'"
    print(f"    -> Got {len(response)} chars of code")
    print(f"    -> First line: {response.split(chr(10))[0][:60]}")

groq_key = os.getenv("GROQ_API_KEY", "")
if groq_key and not groq_key.startswith("sk-your"):
    test("Live Triage API call", test_live_triage)
    test("Live Reasoning API call", test_live_reasoning)
else:
    print(f"  ⏭️  Skipped (no GROQ_API_KEY found in .env)")


# ═══════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════
print("\n" + "="*60)
print("RESULTS SUMMARY")
print("="*60)

passed = sum(1 for _, ok in results if ok)
failed = sum(1 for _, ok in results if not ok)

for name, ok in results:
    print(f"  {PASS if ok else FAIL} {name}")

print(f"\n  Total: {passed} passed, {failed} failed out of {len(results)}")

if failed == 0:
    print("\n  ALL TESTS PASSED -- Engine v3 is ready for deployment!")
else:
    print(f"\n  WARNING: {failed} test(s) failed. Fix them before deploying.")

sys.exit(0 if failed == 0 else 1)
