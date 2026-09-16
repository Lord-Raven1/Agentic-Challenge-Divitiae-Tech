"""Checks the dashboard shows exactly what Member 1 + Member 2 produce.

Run from anywhere:  python source/member3/dashboard_integration_test.py
"""
import io
import json
import os
import sys
import tempfile
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from src.agent_bridge import build_ticks_from_csv, to_json_line  # noqa: E402  (also puts member1/2 on sys.path)
from src.config import DATA_DIR, PREDICTIONS_JSONL, REPO_ROOT  # noqa: E402

import pipeline  # noqa: E402  (member2)
from parser import parse_reports  # noqa: E402  (member1)
from tracker import IncidentTracker  # noqa: E402  (member1)

DATASETS = ["campus_reports.csv", "campus_reports_dirty_test.csv",
            "campus_reports_llm_dirty.csv", "campus_reports_llm_massive.csv"]


def pipeline_output(csv_path):
    with tempfile.TemporaryDirectory() as tmp:
        out, log = os.path.join(tmp, "p.jsonl"), os.path.join(tmp, "log.jsonl")
        pipeline.run(csv_path, pipeline.DEFAULT_SERVICES, out, log)
        with open(out, encoding="utf-8") as f:
            lines = f.read().splitlines()
        with open(log, encoding="utf-8") as f:
            log_rows = [json.loads(line) for line in f]
    return lines, log_rows


def check_dataset(name):
    path = os.path.join(DATA_DIR, name)
    ticks = build_ticks_from_csv(path)
    lines, log_rows = pipeline_output(path)

    # 1. Member 2: identical predictions.jsonl lines, in the same order.
    dash_lines = [to_json_line(t.prediction.model_dump()) for t in ticks]
    assert len(dash_lines) == len(lines), f"{name}: {len(dash_lines)} ticks vs {len(lines)} predictions"
    for i, (d, p) in enumerate(zip(dash_lines, lines)):
        assert d == p, f"{name} line {i + 1}:\n dashboard {d}\n pipeline  {p}"

    # 2. Decision log view: same reason / decision fields as member2's log.
    for t, row in zip(ticks, log_rows):
        dec = t.decision
        assert (dec.report_id, dec.incident_id, dec.relationship, dec.severity, dec.confidence,
                dec.status, dec.human_review, dec.concise_reason) == (
            row["report_id"], row["incident_id"], row["relationship"], row["severity"], row["confidence"],
            row["incident_status"], row["human_review"], row["reason"]), f"{name} {dec.report_id}: decision log"
        assert [a.model_dump() for a in dec.actions] == row["actions"]

    # 3. Incoming report view: member1's parsed fields, in file order.
    reports = parse_reports(path)
    assert [t.report.report_id for t in ticks] == [r.report_id for r in reports]
    for t, r in zip(ticks, reports):
        assert (t.report.location, t.report.description, t.report.reporter_type, t.report.timestamp) == (
            r.location, r.description, r.reporter_type, r.raw_timestamp), f"{name} {r.report_id}: report"

    # 4. Incident summary view: member1's clustering (report ids per incident)
    #    and member2's final incident state.
    tracker = IncidentTracker()
    for r in reports:
        tracker.process(r)
    final = ticks[-1].incident_states
    member1_clusters = {i.incident_id: i.report_ids for i in tracker.incidents}
    assert {k: v.report_ids for k, v in final.items()} == member1_clusters, f"{name}: incident clusters"
    last_row = {}
    for row in log_rows:
        last_row[row["incident_id"]] = row
    for inc_id, snap in final.items():
        row = last_row[inc_id]
        assert (snap.severity, snap.status, snap.confidence) == (
            row["severity"], row["incident_status"], row["confidence"]), f"{name} {inc_id}: incident state"
        if "incident" in row:
            assert set(row["incident"]["services"]) <= set(snap.services), f"{name} {inc_id}: services"

    # 5. Action history view: one row per emitted action, new vs continued.
    expected = [(row["report_id"], a["type"], a["service_id"]) for row in log_rows for a in row["actions"]]
    history = ticks[-1].all_actions_snapshot
    assert [(a.report_id, a.action_type, a.service_id) for a in history] == expected, f"{name}: actions"
    per_incident = defaultdict(int)
    for a in history:
        per_incident[a.incident_id] += 1
        assert a.is_new_action == (a.action_type not in ("CONTINUE_RESPONSE", "MONITOR", "NO_NEW_ACTION"))

    # 6. Replay: every tick only shows decisions made so far.
    for i in (0, len(ticks) // 2, len(ticks) - 1):
        assert set(ticks[i].incident_states) == {t.prediction.incident_id for t in ticks[:i + 1]}
        assert len(ticks[i].all_actions_snapshot) == sum(len(t.prediction.actions) for t in ticks[:i + 1])

    return len(ticks), len(final), len(history)


def check_committed_predictions():
    """The predictions.jsonl in the repo root matches what the dashboard shows."""
    ticks = build_ticks_from_csv(os.path.join(DATA_DIR, "campus_reports.csv"))
    with open(PREDICTIONS_JSONL, encoding="utf-8") as f:
        committed = f.read().splitlines()
    dash = [to_json_line(t.prediction.model_dump()) for t in ticks]
    mismatched = [i + 1 for i, (a, b) in enumerate(zip(dash, committed)) if a != b]
    assert len(dash) == len(committed) and not mismatched, (
        f"predictions.jsonl is stale (lines {mismatched[:10]}); regenerate with run_predictions.py")

    log_path = os.path.join(REPO_ROOT, "decision_log.jsonl")
    with open(log_path, encoding="utf-8") as f:
        reasons = [json.loads(line)["reason"] for line in f]
    assert reasons == [t.decision.concise_reason for t in ticks], "decision_log.jsonl is stale"


def check_upload_path():
    """An uploaded CSV goes through the same agent as the CLI."""
    from src.data_loader import create_scenario_from_upload

    path = os.path.join(DATA_DIR, "campus_reports_llm_dirty.csv")
    with open(path, "rb") as f:
        buffer = io.BytesIO(f.read())
    buffer.name = "campus_reports_llm_dirty.csv"
    scenario = create_scenario_from_upload(buffer)
    lines, _ = pipeline_output(path)
    assert [to_json_line(t.prediction.model_dump()) for t in scenario.ticks] == lines, "upload path"


def check_views_render():
    """Render every dashboard view headlessly and at several replay positions."""
    from streamlit.testing.v1 import AppTest

    from src.config import VIEW_LIST

    at = AppTest.from_file(os.path.join(HERE, "app.py"), default_timeout=300)
    at.run()
    assert not at.exception, at.exception
    ticks = build_ticks_from_csv(os.path.join(DATA_DIR, "campus_reports.csv"))
    for tick_idx in (0, 75, len(ticks) - 1):
        at.slider(key="scrub_slider").set_value(tick_idx).run()
        assert at.session_state["replay_engine"].current_tick_idx == tick_idx
        tick = ticks[tick_idx]
        for view in VIEW_LIST:
            at.sidebar.radio[0].set_value(view).run()
            assert not at.exception, f"{view} @ tick {tick_idx}: {at.exception}"
            headings = [str(m.value) for m in at.markdown if str(m.value).startswith("### ")]
            assert f"### {view}" in headings, f"clicked {view} but page shows {headings}"
            page = " ".join(str(m.value) for m in at.markdown)
            assert tick.prediction.report_id in page, f"{view} @ {tick_idx}: current report not shown"
            if view == VIEW_LIST[1]:
                df = at.dataframe[0].value
                assert len(df) == tick_idx + 1, f"decision log shows {len(df)} rows at tick {tick_idx}"
                top = df.iloc[0]
                assert (top["Report ID"], top["Incident ID"], top["Relationship"], top["Concise Reason"]) == (
                    tick.decision.report_id, tick.decision.incident_id, tick.decision.relationship,
                    tick.decision.concise_reason)
            if view == VIEW_LIST[2]:
                df = at.dataframe[0].value
                assert set(df["Incident ID"]) == set(tick.incident_states)

    # Every scenario can be selected in turn, including from a late replay position.
    for scenario_id in list(at.session_state["available_scenarios"]) + ["all_reports"]:
        at.sidebar.selectbox[0].set_value(scenario_id).run()
        assert not at.exception, f"scenario {scenario_id}: {at.exception}"
        engine = at.session_state["replay_engine"]
        assert engine.scenario.scenario_id == scenario_id, f"selected {scenario_id}, got {engine.scenario.scenario_id}"


def main():
    failed = False
    for name in DATASETS:
        try:
            n, incidents, actions = check_dataset(name)
            print(f"PASS {name}: {n} reports, {incidents} incidents, {actions} actions match member1/member2")
        except AssertionError as e:
            failed = True
            print(f"FAIL {name}: {e}")
    for label, fn in (("committed predictions.jsonl / decision_log.jsonl", check_committed_predictions),
                      ("CSV upload path", check_upload_path),
                      ("dashboard views render", check_views_render)):
        try:
            fn()
            print(f"PASS {label}")
        except AssertionError as e:
            failed = True
            print(f"FAIL {label}: {e}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
