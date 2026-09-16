"""Stress test: missing fields, malformed timestamps, blank rows, whitespace,
mixed casing, and a row with no report_id. Verifies the parser never crashes
and never reorders, and that the tracker degrades sensibly rather than
throwing on incomplete data.
"""
from parser import parse_reports
from tracker import IncidentTracker

CSV_PATH = "../../04_Development_Data/campus_reports_dirty_test.csv"

with open(CSV_PATH, encoding="utf-8-sig") as f:
    input_row_count = sum(1 for _ in f) - 1  # minus header

reports = parse_reports(CSV_PATH)
print(f"input rows (excluding header): {input_row_count}")
print(f"parsed reports: {len(reports)}  (expect input_row_count - 1, since one row has no report_id)")

# Row order must be preserved exactly as read.
row_indices = [r.row_index for r in reports]
assert row_indices == sorted(row_indices), "rows were reordered!"
print("row order preserved: OK\n")

print("=== Parsed field values ===")
for r in reports:
    ts_status = "OK" if r.timestamp else ("EMPTY" if not r.raw_timestamp else "UNPARSED")
    print(f"{r.report_id:6} row={r.row_index:2} ts={ts_status:8} raw={r.raw_timestamp!r:22} "
          f"loc={r.location!r:25} cat={r.category!r:12} sev={r.reported_severity!r:8} "
          f"reporter={r.reporter_type!r}")

print("\n=== Feeding into IncidentTracker (must not crash) ===")
tracker = IncidentTracker()
for r in reports:
    result = tracker.process(r)
    print(f"{r.report_id:6} -> {result.incident.incident_id} [{result.relationship:12}] "
          f"conf={result.confidence:.2f} loc={r.location!r:25} cat={r.category!r}")

print(f"\n{len(tracker.incidents)} incidents from {len(reports)} reports")
print("NO CRASH: dirty data handled successfully")
