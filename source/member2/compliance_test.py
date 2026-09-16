"""Output-compliance and safety-rule checks for every dev/dirty dataset.

Run from anywhere:  python source/member2/compliance_test.py
"""
import csv
import json
import os
import sys
import tempfile
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pipeline  # noqa: E402
from schema import validate_prediction  # noqa: E402
from services import ServiceDirectory  # noqa: E402

DATA = os.path.join(pipeline.REPO_ROOT, "04_Development_Data")
DATASETS = ["campus_reports.csv", "campus_reports_dirty_test.csv",
            "campus_reports_llm_dirty.csv", "campus_reports_llm_massive.csv"]
ENGAGING = {"DISPATCH", "REQUEST_INSPECTION", "CREATE_TICKET", "NOTIFY"}


def input_report_ids(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [(row.get("report_id") or "").strip() for row in csv.DictReader(f)
                if (row.get("report_id") or "").strip()]


def check(name):
    path = os.path.join(DATA, name)
    service_ids = ServiceDirectory(pipeline.DEFAULT_SERVICES).ids
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "predictions.jsonl")
        pipeline.run(path, pipeline.DEFAULT_SERVICES, out)
        with open(out, encoding="utf-8") as f:
            lines = f.read().splitlines()

    preds = [json.loads(line) for line in lines]  # raises on invalid JSON
    for p in preds:
        validate_prediction(p, service_ids)
    assert [p["report_id"] for p in preds] == input_report_ids(path), f"{name}: report ids/order mismatch"

    engaged = defaultdict(set)
    was_resolved = set()  # a reopened incident may legitimately re-dispatch
    problems = []
    for p in preds:
        inc = p["incident_id"]
        for a in p["actions"]:
            key = (a["type"], a["service_id"])
            if a["type"] in ENGAGING and a["service_id"] in engaged[inc] and inc not in was_resolved:
                problems.append(f"{p['report_id']}: repeat {key} on {inc}")
            if a["type"] in ENGAGING:
                engaged[inc].add(a["service_id"])
        if p["incident_status"] == "RESOLVED":
            was_resolved.add(inc)
        if p["relationship"] == "DUPLICATE" and any(a["type"] in ENGAGING for a in p["actions"]):
            problems.append(f"{p['report_id']}: duplicate caused a new engagement")
        if p["relationship"] == "CONFLICT" and not p["human_review"]:
            problems.append(f"{p['report_id']}: conflict without human review")
        if p["relationship"] == "RESOLUTION" and p["incident_status"] != "RESOLVED":
            problems.append(f"{p['report_id']}: resolution without RESOLVED status")

    counts = defaultdict(int)
    for p in preds:
        counts[p["relationship"]] += 1
    print(f"{name:34} {len(preds):4} lines valid | incidents={len({p['incident_id'] for p in preds}):3} "
          f"| human_review={sum(p['human_review'] for p in preds):3} | {dict(counts)}")
    for problem in problems:
        print("   PROBLEM:", problem)
    return not problems


if __name__ == "__main__":
    ok = all([check(name) for name in DATASETS])
    print("\nALL CHECKS PASSED" if ok else "\nSOME CHECKS FAILED")
    sys.exit(0 if ok else 1)
