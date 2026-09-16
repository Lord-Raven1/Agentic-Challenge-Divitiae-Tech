# Member 2 — Service & Action Rules, Output Compliance

Builds on Member 1's `parser.py` (CSV parsing) and `tracker.py` (incident
correlation). For each report, in file order:

```
parse_reports -> IncidentTracker.process -> DecisionEngine.decide -> predictions.jsonl
```

## Commands

```bash
pip install -r source/member2/requirements.txt
python run_predictions.py --reports 04_Development_Data/campus_reports.csv --output predictions.jsonl --log decision_log.jsonl
python source/member2/compliance_test.py
```

`--log` is optional: it writes the same decisions plus a `reason`, the report
text and an incident snapshot, for the dashboard.

## Files

| File | Role |
|---|---|
| `services.py` | Loads `campus_services.csv`, checks opening hours (e.g. first aid 07:00-19:00 falls back to EMS), normalises messy categories (`cleaning`, `FIRE`, misspellings, missing -> inferred from description), maps evidence to services and picks the engaging action type. |
| `signals.py` | Description keywords: critical/high risk (with negation, e.g. "no flames"), conflict/hedging, control, resolution, worsening, explicit duplicates. |
| `decision_engine.py` | Per-incident state (severity, peak, status, confidence, engaged services, action history) and the rules below. |
| `schema.py` | Enums + `validate_prediction`; every line is validated before it is written. |
| `pipeline.py` | Wires Member 1 + Member 2; a failing report still produces a valid, `human_review: true` line. |
| `compliance_test.py` | Runs all dev/dirty datasets; checks JSON validity, schema, report IDs/order, no repeat engagements, duplicates never dispatch, conflicts always reviewed. |

## Rules

- **No redundant dispatch:** each service is engaged (DISPATCH / REQUEST_INSPECTION / CREATE_TICKET / NOTIFY) once per incident. Later evidence -> `CONTINUE_RESPONSE`; `DUPLICATE` -> `[]`; controlled incidents -> `MONITOR` once, then `[]`. Re-dispatch only if a resolved incident reopens, or a verification turns into a confirmed need.
- **Severity:** reporter severity isn't trusted — CRITICAL without supporting description evidence is capped at HIGH and flagged. Escalates on stronger evidence; de-escalates one step at a time only once controlled; conflicting/hedged reports never lower it.
- **CONFLICT:** hedged or contradicting evidence -> `REQUEST_VERIFICATION` (+ `CONTINUE_RESPONSE` if HIGH+), confidence drops, `human_review: true`.
- **Human review:** conflict/uncertainty, confidence < 0.5, unmappable report, first reaching CRITICAL, reopened incident, closing a formerly CRITICAL incident, security dispatch involving a person (no accusation without a human).
- **Lifecycle:** `INVESTIGATING` (new, LOW/MEDIUM) -> `ACTIVE` (corroborated or HIGH) -> `ESCALATED` (CRITICAL) -> `CONTROLLED` (containment evidence) -> `RESOLVED` (explicit resolution only, `CLOSE_INCIDENT` once). A resolved incident reopens on new hazard evidence.
