"""
Bridge between the dashboard and the team's agent (Member 1 + Member 2).

The dashboard has no decision logic of its own: every report is run through
member2/pipeline.process_reports (Member 1 parser + tracker -> Member 2
decision engine), the exact code path run_predictions.py uses to write
predictions.jsonl. This module only reshapes each decision into a ReplayTick.
"""
import sys
from typing import Dict, Iterable, List

from src.config import MEMBER1_DIR, MEMBER2_DIR, SERVICES_CSV
from src.models import (
    ActionHistoryItem,
    ActionItem,
    CampusReport,
    DecisionLogEntry,
    IncidentSnapshot,
    PredictionOutput,
    ReplayTick,
)

for _path in (str(MEMBER2_DIR), str(MEMBER1_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import pipeline  # noqa: E402  (member2)
from parser import parse_report_rows, parse_reports  # noqa: E402  (member1)
from schema import to_json_line  # noqa: E402,F401  (member2, re-exported for app.py)
from services import ServiceDirectory  # noqa: E402  (member2)

# Mirrors member2's decision_engine action_history "new_action" rule.
NON_NEW_ACTIONS = {"CONTINUE_RESPONSE", "MONITOR", "NO_NEW_ACTION"}

OUTCOME_MAP = {
    "DISPATCH": "DISPATCHED",
    "NOTIFY": "NOTIFIED",
    "CONTINUE_RESPONSE": "MAINTAINED",
    "ESCALATE_RESPONSE": "ESCALATED",
    "REQUEST_INSPECTION": "PENDING_INSPECTION",
    "REQUEST_VERIFICATION": "PENDING_VERIFICATION",
    "CREATE_TICKET": "LOGGED",
    "MONITOR": "MONITORING",
    "CLOSE_INCIDENT": "CLOSED",
}


def _decision_label(actions: List[dict]) -> str:
    if not actions:
        return "NO_NEW_ACTION"
    return " + ".join(f"{a['type']} {a['service_id']}" for a in actions)


def build_ticks_from_csv(csv_path) -> List[ReplayTick]:
    return build_ticks(parse_reports(str(csv_path)))


def build_ticks_from_rows(rows: Iterable[dict]) -> List[ReplayTick]:
    return build_ticks(parse_report_rows(rows))


def build_ticks(reports) -> List[ReplayTick]:
    """Run reports through the team agent, in order, and build replay ticks."""
    service_names = {sid: s.name for sid, s in ServiceDirectory(str(SERVICES_CSV)).services.items()}

    ticks: List[ReplayTick] = []
    action_history: List[ActionHistoryItem] = []
    incidents: Dict[str, dict] = {}

    for report, prediction, log_row in pipeline.process_reports(reports, str(SERVICES_CSV)):
        inc_id = prediction["incident_id"]
        snapshot = log_row.get("incident") or {}
        category = snapshot.get("category") or report.category or "unmapped"

        campus_report = CampusReport(
            report_id=report.report_id,
            timestamp=report.raw_timestamp,
            location=report.location,
            category=report.category,
            reported_severity=report.reported_severity or "UNKNOWN",
            description=report.description,
            reporter_type=report.reporter_type,
            missing_fields=[name for name in ("timestamp", "location", "category", "reported_severity",
                                              "description", "reporter_type")
                            if not getattr(report, "raw_timestamp" if name == "timestamp" else name)],
            is_timestamp_malformed=bool(report.raw_timestamp) and report.timestamp is None,
            clean_location=report.location or "Unknown location",
            clean_category=category,
        )

        pred_model = PredictionOutput(**prediction)
        label = _decision_label(prediction["actions"])

        inc = incidents.get(inc_id)
        previous_confidence = inc["confidence"] if inc else None
        if inc is None:
            inc = incidents[inc_id] = {
                "reports": [], "severity_progression": [], "confidence_progression": [],
                "services": set(), "human_review": False,
            }
        inc.update(
            current_type=category,
            location=snapshot.get("location") or inc.get("location") or campus_report.clean_location,
            severity=prediction["severity"],
            confidence=prediction["confidence"],
            status=prediction["incident_status"],
            action=label,
        )
        inc["reports"].append(campus_report)
        inc["severity_progression"].append(prediction["severity"])
        inc["confidence_progression"].append(prediction["confidence"])
        inc["services"].update(snapshot.get("services") or [])
        inc["services"].update(a["service_id"] for a in prediction["actions"])
        inc["human_review"] = inc["human_review"] or prediction["human_review"]
        inc["assessment"] = (
            f"{len(inc['reports'])} report(s) linked. Status {prediction['incident_status']}, "
            f"severity {prediction['severity']}. Latest ({report.report_id}): {log_row['reason']}"
        )

        decision = DecisionLogEntry(
            report_id=report.report_id,
            incident_id=inc_id,
            relationship=prediction["relationship"],
            severity=prediction["severity"],
            confidence=prediction["confidence"],
            actions=[ActionItem(**a) for a in prediction["actions"]],
            decision=label,
            service=", ".join(dict.fromkeys(a["service_id"] for a in prediction["actions"])) or "-",
            status=prediction["incident_status"],
            concise_reason=log_row["reason"],
            human_review=prediction["human_review"],
            conflict_detected=prediction["relationship"] == "CONFLICT",
            confidence_delta=round(prediction["confidence"] - previous_confidence, 2)
            if previous_confidence is not None else 0.0,
        )

        new_actions = []
        for a in prediction["actions"]:
            item = ActionHistoryItem(
                action_id=f"ACT-{len(action_history) + 1:04d}",
                incident_id=inc_id,
                report_id=report.report_id,
                time=report.raw_timestamp,
                action_type=a["type"],
                service_id=a["service_id"],
                service_name=service_names.get(a["service_id"], a["service_id"]),
                is_new_action=a["type"] not in NON_NEW_ACTIONS,
                outcome_status=OUTCOME_MAP.get(a["type"], "COMPLETED"),
                notes=f"Linked to {report.report_id} ({prediction['relationship']})",
            )
            action_history.append(item)
            new_actions.append(item)

        states = {
            key: IncidentSnapshot(
                incident_id=key,
                current_type=data["current_type"],
                location=data["location"],
                severity=data["severity"],
                confidence=data["confidence"],
                report_ids=[r.report_id for r in data["reports"]],
                reports_count=len(data["reports"]),
                services=sorted(data["services"]),
                status=data["status"],
                action=data["action"],
                human_review=data["human_review"],
                evolving_assessment=data["assessment"],
                reports_history=list(data["reports"]),
                severity_progression=list(data["severity_progression"]),
                confidence_progression=list(data["confidence_progression"]),
            )
            for key, data in incidents.items()
        }

        ticks.append(ReplayTick(
            tick_index=len(ticks),
            report=campus_report,
            prediction=pred_model,
            decision=decision,
            new_actions=new_actions,
            all_actions_snapshot=list(action_history),
            incident_states=states,
            active_incident_id=inc_id,
            narrative=f"Processed {report.report_id}: {prediction['relationship']} -> {inc_id} [{label}]",
        ))

    return ticks
