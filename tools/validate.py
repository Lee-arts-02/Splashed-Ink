#!/usr/bin/env python3
"""Validate Splashed Ink plan and session files against the schemas in docs/schema.

    pip install jsonschema
    python tools/validate.py examples/plan-example.json examples/session-example.json

Besides the schema, session files get a few consistency checks that a schema cannot express
(event order, pointers opened before they move, the end tick covering every event).
"""
import json, sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    sys.exit("This tool needs jsonschema: pip install jsonschema")

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {
    "splashed-ink-plan/v2": ROOT / "docs/schema/plan-v2.schema.json",
    "splashed-ink-session/v1": ROOT / "docs/schema/session-v1.schema.json",
}

def session_checks(doc):
    problems, last, open_ptrs = [], -1, set()
    for n, ev in enumerate(doc["events"]):
        if ev["t"] < last:
            problems.append(f"event {n}: tick {ev['t']} comes after tick {last}")
        last = max(last, ev["t"])
        if ev["e"] == "pd":
            open_ptrs.add(ev["i"])
        elif ev["e"] in ("pm", "pu") and ev["i"] not in open_ptrs:
            problems.append(f"event {n}: pointer {ev['i']} moves or lifts without being down")
        if ev["e"] == "pu":
            open_ptrs.discard(ev["i"])
    if doc["events"] and doc["endTick"] < last:
        problems.append(f"endTick {doc['endTick']} is before the last event at tick {last}")
    return problems

def check(path):
    doc = json.loads(Path(path).read_text())
    fmt = doc.get("format")
    if fmt not in SCHEMAS:
        return [f"unknown format {fmt!r}"]
    schema = json.loads(SCHEMAS[fmt].read_text())
    problems = [f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message[:160]}"
                for e in sorted(jsonschema.Draft202012Validator(schema).iter_errors(doc), key=lambda e: list(map(str, e.absolute_path)))[:20]]
    if not problems and fmt.startswith("splashed-ink-session"):
        problems += session_checks(doc)
    return problems

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    bad = 0
    for p in sys.argv[1:]:
        issues = check(p)
        print(("OK    " if not issues else "FAIL  ") + p)
        for i in issues:
            print("      " + i)
        bad += bool(issues)
    sys.exit(1 if bad else 0)
