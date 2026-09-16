from parser import parse_reports
from tracker import IncidentTracker

CSV_PATH = "../../04_Development_Data/campus_reports_llm_dirty.csv"

with open(CSV_PATH, encoding="utf-8-sig") as f:
    input_row_count = sum(1 for _ in f) - 1

reports = parse_reports(CSV_PATH)
print(f"input rows (excluding header): {input_row_count}")
print(f"parsed reports: {len(reports)}\n")

row_indices = [r.row_index for r in reports]
assert row_indices == sorted(row_indices), "rows were reordered!"
print("row order preserved: OK\n")

for r in reports:
    print(f"{r.report_id:6} row={r.row_index:2} ts={r.raw_timestamp!r:22} "
          f"loc={r.location!r:20} cat={r.category!r:14} sev={r.reported_severity!r:9} "
          f"reporter={r.reporter_type!r:12} desc={r.description[:40]!r}")

print("\n=== Feeding into IncidentTracker (must not crash) ===")
tracker = IncidentTracker()
for r in reports:
    result = tracker.process(r)
    print(f"{r.report_id:6} -> {result.incident.incident_id} [{result.relationship:12}] conf={result.confidence:.2f}")

print(f"\n{len(tracker.incidents)} incidents from {len(reports)} reports")
print("NO CRASH: LLM-generated dirty data handled successfully")
