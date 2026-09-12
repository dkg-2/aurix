import json

data = json.load(open('ai-engine-core/verified-results/verified_report_test-local-002.json'))

print("=" * 60)
print("SCAN RESULT SUMMARY")
print("=" * 60)
print(f"Scan ID: {data['scan_id']}")
print(f"URL: {data['url']}")
print(f"Total Findings: {data['summary']['total_findings']}")
print(f"Exploitable: {data['summary']['exploitable_count']}")
print(f"Neutralized: {data['summary']['neutralized_count']}")
print(f"Elapsed: {data['summary']['elapsed_seconds']}s")
print(f"Engine: {data['summary']['scan_engine']}")

verified = [f for f in data['findings'] if f.get('verified')]
print(f"\n{'=' * 60}")
print(f"VERIFIED FINDINGS ({len(verified)})")
print(f"{'=' * 60}")

for i, f in enumerate(verified, 1):
    print(f"\n--- Finding {i} ---")
    print(f"  Title: {f.get('title')}")
    print(f"  File: {f.get('file')}:{f.get('line')}")
    print(f"  Severity: {f.get('severity')}")
    print(f"  Wargame: {f.get('wargame_status', 'N/A')}")
    reasoning = f.get('ai_reasoning', 'N/A')
    if len(reasoning) > 200:
        reasoning = reasoning[:200] + "..."
    print(f"  AI Reasoning: {reasoning}")
    poc = f.get('poc_script', '')
    if poc:
        print(f"  PoC Script: ({len(poc)} chars)")
    patch = f.get('patch_code', '')
    if patch:
        print(f"  Patch Code: ({len(patch)} chars)")

# Category breakdown
cats = {}
for f in data['findings']:
    cat = f.get('category', 'unknown')
    cats[cat] = cats.get(cat, 0) + 1

print(f"\n{'=' * 60}")
print("CATEGORY BREAKDOWN")
print(f"{'=' * 60}")
for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
    print(f"  {cat}: {count}")
