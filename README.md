# Campus Crisis Agent — Divitiae Tech

## Commands

Run from the repository root.

```bash
pip install -r requirements.txt
```

```bash
python -m streamlit run source/member3/app.py
```

```bash
python run_predictions.py --reports 04_Development_Data/campus_reports.csv --output predictions.jsonl --log decision_log.jsonl
```

No environment variables or API keys are required.

## Layout

| Path | Owner | Role |
|---|---|---|
| `source/member1/` | Member 1 | CSV parsing (`parser.py`) and incident correlation (`tracker.py`, `matching.py`). |
| `source/member2/` | Member 2 | Decision engine, service rules and `predictions.jsonl` compliance. See its README. |
| `source/member3/` | Member 3 | Streamlit dashboard: Incoming Report, Decision Log, Incident Summary and Action History views with sequential replay. |
| `04_Development_Data/` | — | Development reports and campus service directory. |

The dashboard has no decision logic of its own. `source/member3/src/agent_bridge.py` runs each report through
`member2/pipeline.process_reports` — the same code path `run_predictions.py` uses — so the dashboard always shows the
same decisions as `predictions.jsonl`.

## Tests

```bash
python source/member2/compliance_test.py
```

```bash
python source/member3/dashboard_integration_test.py
```

The dashboard test checks, for every development dataset, that the dashboard's predictions, decision log, incident
clusters and action history match Member 1 and Member 2's output line for line, that the committed
`predictions.jsonl` / `decision_log.jsonl` are up to date, that CSV upload uses the same agent, and that every view
renders and responds to view and scenario switching.
