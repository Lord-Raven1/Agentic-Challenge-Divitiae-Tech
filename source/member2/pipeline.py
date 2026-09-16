"""End-to-end run: Member 1 parser + tracker -> Member 2 decision engine ->
predictions.jsonl (and an optional richer decision log for the dashboard).
"""
import json
import os
import sys
import traceback
from typing import List

_HERE = os.path.dirname(os.path.abspath(__file__))
_MEMBER1 = os.path.join(os.path.dirname(_HERE), "member1")
for path in (_HERE, _MEMBER1):
    if path not in sys.path:
        sys.path.insert(0, path)

from parser import parse_reports  # noqa: E402  (member1)
from tracker import IncidentTracker  # noqa: E402  (member1)

from decision_engine import Decision, DecisionEngine  # noqa: E402
from schema import to_json_line, validate_prediction  # noqa: E402
from services import ServiceDirectory  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))
DEFAULT_REPORTS = os.path.join(REPO_ROOT, "04_Development_Data", "campus_reports.csv")
DEFAULT_SERVICES = os.path.join(REPO_ROOT, "04_Development_Data", "campus_services.csv")


def run(reports_csv: str = DEFAULT_REPORTS, services_csv: str = DEFAULT_SERVICES,
        output_path: str = "predictions.jsonl", log_path: str = None) -> List[dict]:
    directory = ServiceDirectory(services_csv)
    tracker = IncidentTracker()
    engine = DecisionEngine(directory)

    predictions, log_rows = [], []
    for report in parse_reports(reports_csv):
        correlation = None
        try:
            correlation = tracker.process(report)
            decision: Decision = engine.decide(correlation)
            prediction = decision.prediction
            log_rows.append({
                **prediction,
                "reason": decision.reason,
                "timestamp": report.raw_timestamp,
                "location": report.location,
                "category": report.category,
                "description": report.description,
                "reporter_type": report.reporter_type,
                "incident": decision.incident_snapshot,
            })
        except Exception:  # never drop a report: emit a flagged safe line
            traceback.print_exc()
            prediction = DecisionEngine.fallback_prediction(
                report.report_id,
                correlation.incident.incident_id if correlation else None,
                correlation.relationship if correlation else "NEW",
            )
            log_rows.append({**prediction, "reason": "internal error: flagged for human review"})
        validate_prediction(prediction, directory.ids)
        predictions.append(prediction)

    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        for prediction in predictions:
            f.write(to_json_line(prediction) + "\n")

    if log_path:
        with open(log_path, "w", encoding="utf-8", newline="\n") as f:
            for row in log_rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return predictions
