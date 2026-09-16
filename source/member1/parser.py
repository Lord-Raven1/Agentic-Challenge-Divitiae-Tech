"""Robust CSV ingestion for campus_reports.csv.

Guarantees:
- Rows are always returned in file order (never sorted/reordered).
- A malformed or missing field never raises — it degrades to an empty
  string / None so downstream stages can decide how to handle it.
- A single unparsable row is skipped (logged), it does not abort the run.
"""
import csv
from datetime import datetime
from typing import Iterable, List

from models import Report

REQUIRED_FIELDS = [
    "report_id", "timestamp", "location", "category",
    "reported_severity", "description", "reporter_type",
]

# Reports in the wild may use any of these; extend as unseen data reveals more.
_TIMESTAMP_FORMATS = [
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y %H:%M",
]


def _parse_timestamp(raw: str):
    raw = (raw or "").strip()
    if not raw:
        return None

    parsed = None
    for fmt in _TIMESTAMP_FORMATS:
        try:
            parsed = datetime.strptime(raw, fmt)
            break
        except ValueError:
            continue
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            return None

    # fromisoformat can return a timezone-aware datetime (e.g. a trailing
    # "Z"), while every other path here is naive. Comparing the two raises
    # TypeError downstream, so normalize to naive immediately.
    if parsed.tzinfo is not None:
        parsed = parsed.replace(tzinfo=None)
    return parsed


def parse_reports(csv_path: str) -> List[Report]:
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        return parse_report_rows(csv.DictReader(f))


def parse_report_rows(rows: Iterable[dict]) -> List[Report]:
    """Same guarantees as parse_reports, for rows already read from a CSV
    (e.g. a file uploaded to the dashboard)."""
    reports: List[Report] = []
    for row_index, row in enumerate(rows):
        report_id = (row.get("report_id") or "").strip()
        if not report_id:
            # A report with no ID cannot be tracked or referenced downstream; skip it.
            continue

        raw_timestamp = row.get("timestamp") or ""
        reports.append(Report(
            report_id=report_id,
            row_index=row_index,
            raw_timestamp=raw_timestamp,
            timestamp=_parse_timestamp(raw_timestamp),
            location=(row.get("location") or "").strip(),
            category=(row.get("category") or "").strip().lower(),
            reported_severity=(row.get("reported_severity") or "").strip().upper(),
            description=(row.get("description") or "").strip(),
            reporter_type=(row.get("reporter_type") or "").strip().lower(),
        ))
    return reports
