"""
Data Ingestion and Scenario Loading Engine for Campus Crisis Agent.
Handles campus_reports.csv, scenario slicing for the 4 rubric scenarios,
and arbitrary user-uploaded test CSV files.
"""
import csv
import io
from pathlib import Path
from typing import Dict, List, Any, Optional
import streamlit as st

from src.models import CampusScenario
from src.agent_bridge import build_ticks_from_rows
from src.config import REPORTS_CSV


def load_raw_csv_rows(file_path: Path) -> List[Dict[str, Any]]:
    """Read a CSV file preserving row order without reordering."""
    rows = []
    if not file_path.exists():
        return rows
    with open(file_path, mode="r", newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows


def parse_csv_stream(file_buffer) -> List[Dict[str, Any]]:
    """Parse an uploaded file buffer as CSV rows."""
    content = file_buffer.getvalue().decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(content))
    return [dict(row) for row in reader]


def build_scenario_from_rows(
    scenario_id: str,
    title: str,
    description: str,
    badge: str,
    rows: List[Dict[str, Any]],
) -> CampusScenario:
    """Run the team agent (Member 1 + Member 2) through the rows in order."""
    ticks = build_ticks_from_rows(rows)

    return CampusScenario(
        scenario_id=scenario_id,
        title=title,
        description=description,
        badge=badge,
        total_ticks=len(ticks),
        ticks=ticks,
    )


@st.cache_data(show_spinner=False)
def load_all_scenarios() -> Dict[str, CampusScenario]:
    """Load all standard campus benchmark scenarios from campus_reports.csv."""
    scenarios: Dict[str, CampusScenario] = {}
    all_rows = load_raw_csv_rows(REPORTS_CSV)
    if not all_rows:
        return scenarios

    # 1. Full feed
    scenarios["all_reports"] = build_scenario_from_rows(
        scenario_id="all_reports",
        title=f"Full Campus Feed ({len(all_rows)} Reports)",
        description=f"Sequential replay of all {len(all_rows)} campus crisis reports in file order across all incidents.",
        badge="FULL FEED",
        rows=all_rows,
    )

    # 2. Rubric Scenarios
    scenario_configs = [
        (
            "network_outage",
            "Scenario 1: Network Outage",
            "Campus-wide Wi-Fi degradation escalating to learning platform and authentication failures.",
            "SCENARIO 1",
            lambda r: r.get("category") == "it" or "campus-wide" in str(r.get("location", "")).lower() or "wi-fi" in str(r.get("description", "")).lower(),
        ),
        (
            "smoke_electrical",
            "Scenario 2: Smoke / Electrical Incident",
            "Engineering Block E3 burning smell, socket smoke, and escalating fire response.",
            "SCENARIO 2",
            lambda r: "e3" in str(r.get("location", "")).lower() or r.get("category") in ["fire", "electrical"] or "smoke" in str(r.get("description", "")).lower(),
        ),
        (
            "contractor_check",
            "Scenario 3: Contractor Verification",
            "Science Block loading bay unknown individual with tools escalating to authorization check.",
            "SCENARIO 3",
            lambda r: "science block" in str(r.get("location", "")).lower() or r.get("category") == "security" or "contractor" in str(r.get("description", "")).lower(),
        ),
        (
            "lift_accessibility",
            "Scenario 4: Lift / Accessibility Incident",
            "Admin Block Lift A failure leaving wheelchair user waiting for upper floor access.",
            "SCENARIO 4",
            lambda r: "lift" in str(r.get("location", "")).lower() or r.get("category") in ["accessibility", "facilities"] and ("lift" in str(r.get("location", "")).lower() or "wheelchair" in str(r.get("description", "")).lower()),
        ),
    ]

    for s_id, s_title, s_desc, s_badge, s_filter in scenario_configs:
        filtered_rows = [r for r in all_rows if s_filter(r)]
        if filtered_rows:
            scenarios[s_id] = build_scenario_from_rows(
                scenario_id=s_id,
                title=s_title,
                description=s_desc,
                badge=s_badge,
                rows=filtered_rows,
            )

    return scenarios


def create_scenario_from_upload(uploaded_file) -> Optional[CampusScenario]:
    """Create a scenario on the fly from an uploaded unseen test CSV."""
    try:
        rows = parse_csv_stream(uploaded_file)
        if not rows:
            return None
        return build_scenario_from_rows(
            scenario_id=f"upload_{uploaded_file.name}",
            title=f"Uploaded Test: {uploaded_file.name}",
            description=f"Processed unseen test dataset containing {len(rows)} reports.",
            badge="CUSTOM CSV",
            rows=rows,
        )
    except Exception as e:
        st.error(f"Failed to process uploaded CSV: {e}")
        return None
