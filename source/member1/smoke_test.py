from collections import defaultdict

from parser import parse_reports
from tracker import IncidentTracker

reports = parse_reports("../../04_Development_Data/campus_reports.csv")
print(f"parsed {len(reports)} reports\n")

tracker = IncidentTracker()
results = [tracker.process(r) for r in reports]

for result in results:
    r = result.report
    flag = "CONFLICT?" if result.conflict_candidate else ""
    print(f"{r.report_id:5} -> {result.incident.incident_id} "
          f"[{result.relationship:12}] conf={result.confidence:.2f} {flag:10}"
          f"loc={r.location!r:35} cat={r.category:15} desc={r.description[:60]}")

print(f"\n{len(tracker.incidents)} incidents from {len(reports)} reports\n")

print("=== Grouped by incident (for eyeballing merges) ===")
by_incident = defaultdict(list)
for result in results:
    by_incident[result.incident.incident_id].append(result)

for incident_id, group in by_incident.items():
    inc = group[0].incident
    print(f"\n{incident_id} | {inc.category} | {inc.location} | severity={inc.severity} | {len(group)} reports")
    for result in group:
        r = result.report
        print(f"    {r.report_id:5} [{result.relationship:12}] loc={r.location!r:35} cat={r.category:12} {r.description[:60]}")
