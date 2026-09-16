"""Final safety pass: feed every test dataset we've built through one
continuous parser + tracker run, in sequence, to confirm nothing crashes
and row order/IDs stay intact across the full combined volume before we
hand this off / commit.
"""
import time

from parser import parse_reports
from tracker import IncidentTracker

DATASETS = [
    ("dev (150 clean)", "../../04_Development_Data/campus_reports.csv"),
    ("hand-written dirty", "../../04_Development_Data/campus_reports_dirty_test.csv"),
    ("LLM dirty (schema-valid)", "../../04_Development_Data/campus_reports_llm_dirty.csv"),
    ("LLM massive (300)", "../../04_Development_Data/campus_reports_llm_massive.csv"),
]

tracker = IncidentTracker()
seen_report_ids = set()
total_reports = 0
t_start = time.time()

for label, path in DATASETS:
    reports = parse_reports(path)
    row_indices = [r.row_index for r in reports]
    assert row_indices == sorted(row_indices), f"{label}: rows reordered!"

    dupes = [r.report_id for r in reports if r.report_id in seen_report_ids]
    if dupes:
        print(f"NOTE: {label} reuses report_ids also seen earlier: {dupes[:5]}{'...' if len(dupes) > 5 else ''}")

    for r in reports:
        seen_report_ids.add(r.report_id)
        tracker.process(r)
        total_reports += 1

    print(f"{label:28} {len(reports):4} reports processed, "
          f"running total incidents={len(tracker.incidents)}, total reports={total_reports}")

elapsed = time.time() - t_start
print(f"\nALL DATASETS PROCESSED WITHOUT CRASHING")
print(f"total reports: {total_reports}")
print(f"total incidents: {len(tracker.incidents)}")
print(f"total time: {elapsed:.3f}s ({elapsed / total_reports * 1000:.2f}ms/report)")
