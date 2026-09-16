"""Output contract for predictions.jsonl (Technical and Submission Guide).

Everything that leaves the agent passes through `to_prediction` +
`validate_prediction`, so an out-of-contract value can never reach the file.
"""
import json
import math

RELATIONSHIPS = ("NEW", "UPDATE", "CORROBORATION", "CONFLICT", "DUPLICATE", "RESOLUTION")
SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
STATUSES = ("INVESTIGATING", "ACTIVE", "ESCALATED", "CONTROLLED", "RESOLVED")
ACTION_TYPES = (
    "DISPATCH", "NOTIFY", "REQUEST_INSPECTION", "REQUEST_VERIFICATION",
    "ESCALATE_RESPONSE", "CONTINUE_RESPONSE", "CREATE_TICKET", "MONITOR",
    "CLOSE_INCIDENT", "NO_NEW_ACTION",
)

# Key order matches the guide's example so the file diffs cleanly against it.
PREDICTION_KEYS = (
    "report_id", "incident_id", "relationship", "severity", "confidence",
    "actions", "incident_status", "human_review",
)


class SchemaError(ValueError):
    pass


def validate_prediction(pred: dict, service_ids=None) -> None:
    if tuple(pred.keys()) != PREDICTION_KEYS:
        raise SchemaError(f"keys {list(pred.keys())} != {list(PREDICTION_KEYS)}")
    if not isinstance(pred["report_id"], str) or not pred["report_id"]:
        raise SchemaError("report_id must be a non-empty string")
    if not isinstance(pred["incident_id"], str) or not pred["incident_id"]:
        raise SchemaError("incident_id must be a non-empty string")
    if pred["relationship"] not in RELATIONSHIPS:
        raise SchemaError(f"bad relationship {pred['relationship']!r}")
    if pred["severity"] not in SEVERITIES:
        raise SchemaError(f"bad severity {pred['severity']!r}")
    if pred["incident_status"] not in STATUSES:
        raise SchemaError(f"bad incident_status {pred['incident_status']!r}")
    conf = pred["confidence"]
    if isinstance(conf, bool) or not isinstance(conf, (int, float)) or math.isnan(conf) or not 0 <= conf <= 1:
        raise SchemaError(f"bad confidence {conf!r}")
    if not isinstance(pred["human_review"], bool):
        raise SchemaError("human_review must be a boolean")
    if not isinstance(pred["actions"], list):
        raise SchemaError("actions must be a list")
    for action in pred["actions"]:
        if not isinstance(action, dict) or set(action.keys()) != {"type", "service_id"}:
            raise SchemaError(f"bad action shape {action!r}")
        if action["type"] not in ACTION_TYPES:
            raise SchemaError(f"bad action type {action['type']!r}")
        if service_ids is not None and action["service_id"] not in service_ids:
            raise SchemaError(f"unknown service_id {action['service_id']!r}")


def to_json_line(pred: dict) -> str:
    return json.dumps(pred, ensure_ascii=False, separators=(", ", ": "))
