import time
from collections import Counter

from parser import parse_reports
from tracker import IncidentTracker

CSV_PATH = "../../04_Development_Data/campus_reports_llm_massive.csv"

with open(CSV_PATH, encoding="utf-8-sig") as f:
    input_row_count = sum(1 for _ in f) - 1

t0 = time.time()
reports = parse_reports(CSV_PATH)
parse_time = time.time() - t0

print(f"input rows (excluding header): {input_row_count}")
print(f"parsed reports: {len(reports)}")
print(f"parse time: {parse_time:.3f}s")

row_indices = [r.row_index for r in reports]
assert row_indices == sorted(row_indices), "rows were reordered!"
print("row order preserved: OK\n")

t0 = time.time()
tracker = IncidentTracker()
results = []
for r in reports:
    result = tracker.process(r)
    results.append(result)
process_time = time.time() - t0

print(f"processed {len(results)} reports through tracker in {process_time:.3f}s "
      f"({process_time / max(len(results),1)*1000:.1f}ms/report)")
print(f"NO CRASH on {len(reports)} report, {len(tracker.incidents)} incidents formed\n")

rel_counts = Counter(r.relationship for r in results)
print("=== Relationship distribution ===")
for rel, count in rel_counts.most_common():
    print(f"  {rel:14} {count}")

conflict_count = sum(1 for r in results if r.conflict_candidate)
print(f"\nconflict_candidate flagged: {conflict_count}")

incident_sizes = Counter(r.incident.incident_id for r in results)
sizes = sorted(incident_sizes.values(), reverse=True)
print(f"\n=== Incident size distribution ===")
print(f"total incidents: {len(incident_sizes)}")
print(f"largest incident: {sizes[0]} reports")
print(f"singleton incidents (1 report): {sum(1 for s in sizes if s == 1)}")
print(f"top 10 incident sizes: {sizes[:10]}")

missing_ts = sum(1 for r in reports if r.timestamp is None)
missing_loc = sum(1 for r in reports if not r.location)
missing_cat = sum(1 for r in reports if not r.category)
missing_sev = sum(1 for r in reports if not r.reported_severity)
missing_desc = sum(1 for r in reports if not r.description)
missing_reporter = sum(1 for r in reports if not r.reporter_type)
print(f"\n=== Missing-field counts (post-parse) ===")
print(f"missing/unparsed timestamp: {missing_ts}")
print(f"missing location: {missing_loc}")
print(f"missing category: {missing_cat}")
print(f"missing severity: {missing_sev}")
print(f"missing description: {missing_desc}")
print(f"missing reporter_type: {missing_reporter}")
