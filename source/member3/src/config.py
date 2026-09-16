"""
Application Configuration and Constants for Campus Crisis Agent Dashboard.
Member 3 Deliverable - Divitiae Tech.
"""
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent  # source/member3
REPO_ROOT = BASE_DIR.parent.parent
MEMBER1_DIR = REPO_ROOT / "source" / "member1"
MEMBER2_DIR = REPO_ROOT / "source" / "member2"
DATA_DIR = REPO_ROOT / "04_Development_Data"
REPORTS_CSV = DATA_DIR / "campus_reports.csv"
SERVICES_CSV = DATA_DIR / "campus_services.csv"
PREDICTIONS_JSONL = REPO_ROOT / "predictions.jsonl"

# 4 Required Views
VIEW_INCOMING_REPORT = "Incoming Report"
VIEW_DECISION_LOG = "Decision Log"
VIEW_INCIDENT_SUMMARY = "Incident Summary"
VIEW_ACTION_HISTORY = "Action History"

VIEW_LIST = [
    VIEW_INCOMING_REPORT,
    VIEW_DECISION_LOG,
    VIEW_INCIDENT_SUMMARY,
    VIEW_ACTION_HISTORY,
]

# Required Contract Enums
RELATIONSHIPS = [
    "NEW",
    "UPDATE",
    "CORROBORATION",
    "CONFLICT",
    "DUPLICATE",
    "RESOLUTION",
]

SEVERITIES = [
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
]

INCIDENT_STATUSES = [
    "INVESTIGATING",
    "ACTIVE",
    "ESCALATED",
    "CONTROLLED",
    "RESOLVED",
]

ACTION_TYPES = [
    "DISPATCH",
    "NOTIFY",
    "REQUEST_INSPECTION",
    "REQUEST_VERIFICATION",
    "ESCALATE_RESPONSE",
    "CONTINUE_RESPONSE",
    "CREATE_TICKET",
    "MONITOR",
    "CLOSE_INCIDENT",
    "NO_NEW_ACTION",
]

# Color Palette (Dark Theme / Clean Observability)
THEME = {
    "background": "#0B0F19",
    "surface": "#111827",
    "surface_alt": "#1F2937",
    "surface_border": "#374151",
    "primary": "#6366F1",       # Indigo-500
    "accent": "#06B6D4",        # Cyan-500
    "text": "#F9FAFB",
    "text_muted": "#9CA3AF",
}

SEVERITY_COLORS = {
    "CRITICAL": "#EF4444",  # Red
    "HIGH": "#F97316",      # Orange
    "MEDIUM": "#F59E0B",    # Amber
    "LOW": "#10B981",       # Emerald
}

STATUS_COLORS = {
    "INVESTIGATING": "#3B82F6",  # Blue
    "ACTIVE": "#F59E0B",         # Amber
    "ESCALATED": "#EF4444",      # Red
    "CONTROLLED": "#8B5CF6",     # Purple
    "RESOLVED": "#10B981",       # Green
}

RELATIONSHIP_COLORS = {
    "NEW": "#3B82F6",            # Blue
    "UPDATE": "#6366F1",         # Indigo
    "CORROBORATION": "#10B981",  # Emerald
    "CONFLICT": "#EC4899",       # Hot Pink / Rose
    "DUPLICATE": "#6B7280",      # Gray
    "RESOLUTION": "#14B8A6",     # Teal
}

# 4 Official Benchmark Scenarios from Rubric Guide
BENCHMARK_SCENARIOS = {
    "all_reports": {
        "id": "all_reports",
        "title": "Full Campus Stream (All 150 Reports)",
        "description": "Sequential processing of all 150 campus crisis reports in file order.",
        "badge": "FULL FEED",
        "filter": lambda r: True,
    },
    "network_outage": {
        "id": "network_outage",
        "title": "Scenario 1: Network Outage",
        "description": "Campus-wide Wi-Fi degradation escalating to learning platform and authentication failures.",
        "badge": "SCENARIO 1",
        "filter": lambda r: r.get("category") == "it" or "campus-wide" in str(r.get("location", "")).lower() or "wi-fi" in str(r.get("description", "")).lower(),
    },
    "smoke_electrical": {
        "id": "smoke_electrical",
        "title": "Scenario 2: Smoke / Electrical Incident",
        "description": "Engineering Block E3 burning smell, socket smoke, and escalating fire response.",
        "badge": "SCENARIO 2",
        "filter": lambda r: "e3" in str(r.get("location", "")).lower() or r.get("category") in ["fire", "electrical"] or "smoke" in str(r.get("description", "")).lower(),
    },
    "contractor_check": {
        "id": "contractor_check",
        "title": "Scenario 3: Contractor Verification",
        "description": "Science Block loading bay unknown individual with tools escalating to authorization check.",
        "badge": "SCENARIO 3",
        "filter": lambda r: "science block" in str(r.get("location", "")).lower() or r.get("category") == "security" or "contractor" in str(r.get("description", "")).lower(),
    },
    "lift_accessibility": {
        "id": "lift_accessibility",
        "title": "Scenario 4: Lift / Accessibility Incident",
        "description": "Admin Block Lift A failure leaving wheelchair user waiting for upper floor access.",
        "badge": "SCENARIO 4",
        "filter": lambda r: "lift" in str(r.get("location", "")).lower() or r.get("category") in ["accessibility", "facilities"] and ("lift" in str(r.get("location", "")).lower() or "wheelchair" in str(r.get("description", "")).lower()),
    },
}

# Replay speed settings (seconds per tick)
REPLAY_SPEED_MAP = {
    "0.5x (Slow - 3.0s)": 3.0,
    "1.0x (Normal - 1.5s)": 1.5,
    "2.0x (Fast - 0.7s)": 0.7,
    "5.0x (Turbo - 0.2s)": 0.2,
}
