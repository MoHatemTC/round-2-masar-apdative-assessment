import json
import os

SOURCE_PATH = "data/sample_question_bank.json"
OUTPUT_PATH = "backend/tests/golden/questions.json"

SOURCE_REFS = ["AIE-1-Q02", "AIE-4-Q03", "AIE-6-Q01", "AIE-3-Q02", "AIE-5-Q01"]

RUBRIC_KEYS = ("evaluation_criteria", "expected_insights", "rubric")

with open(SOURCE_PATH, "r", encoding="utf-8") as f:
    questions = json.load(f)

# Guard against duplicate source_refs in the bank silently picking the wrong one.
by_ref: dict[str, list[dict]] = {}
for q in questions:
    by_ref.setdefault(q.get("source_ref"), []).append(q)

found = {}
missing = []
warnings = []

for ref in SOURCE_REFS:
    matches = by_ref.get(ref, [])
    if not matches:
        missing.append(ref)
        continue
    if len(matches) > 1:
        warnings.append(f"{ref}: {len(matches)} entries share this source_ref — using the first one")

    match = matches[0]
    body = match.get("body")
    payload = match.get("payload") or {}

    if not body or not body.strip():
        warnings.append(f"{ref}: empty/missing body")

    has_rubric = any(payload.get(k) for k in RUBRIC_KEYS)
    has_test_cases = bool(payload.get("test_cases"))
    if not has_rubric and not has_test_cases:
        warnings.append(
            f"{ref}: payload has neither a rubric ({'/'.join(RUBRIC_KEYS)}) nor test_cases — "
            f"grade_answer will return score=None, flagged=True for every case using this ref"
        )

    found[ref] = {"body": body, "payload": payload}

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(found, f, indent=2)

print(f"Found {len(found)} / {len(SOURCE_REFS)}")
if missing:
    print("MISSING:", missing)
if warnings:
    print("WARNINGS:")
    for w in warnings:
        print(f"  - {w}")
if not missing and not warnings:
    print(f"Wrote {OUTPUT_PATH}")
elif not missing:
    print(f"Wrote {OUTPUT_PATH} (with warnings above — check before running the eval suite)")