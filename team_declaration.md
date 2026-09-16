# Team Declaration & Submission Statement

**Challenge:** Campus Crisis Agent (Student Challenge 2026)  
**Team Name:** Divitiae Tech  
**Project Title:** Autonomous Campus Crisis Agent & Sequential Replay Operations Center  
**Repository Snapshot:** `Lord-Raven1/Agentic-Challenge-Divitiae-Tech`  
**Submission Date:** September 16, 2026  

---

## 1. Team Composition & Role Contributions

In accordance with the challenge brief rules requiring three-student teams, responsibilities were divided as follows:

| Team Member | Role Title | Core Contributions & Ownership |
| :--- | :--- | :--- |
| **Member 1** | **Core Agent & Correlation Logic** | • Robust ingestion of `campus_reports.csv` and unseen dirty CSVs (handling missing fields, malformed timestamps, without reordering).<br/>• In-memory clustering state (`incident_id`, active status, severity, services).<br/>• Pairwise/semantic affinity scoring (location, category, temporal proximity, text tokens) to classify `NEW`, `UPDATE`, `CORROBORATION`, `DUPLICATE`, `CONFLICT`, `RESOLUTION`. |
| **Member 2** | **Decision Engine & Prediction Exporter** | • Campus services mapping rules via `campus_services.csv`.<br/>• Safety rules & deduplication: avoids unnecessary repeat dispatches by emitting `CONTINUE_RESPONSE` or `[]`.<br/>• Uncertainty and risk flagging (`human_review: true` on conflicting accounts or critical life safety).<br/>• Strict output compliance with `predictions.jsonl` schema and enums. |
| **Member 3 (This Lead Submission)** | **Dashboard, Replay & Documentation** | • **Streamlit SOC Dashboard:** 4 required views (`Incoming Report`, `Decision Log`, `Incident Summary`, `Action History`).<br/>• **Sequential Replay Engine:** Chronological stepping, timeline scrubbing, speed control, and live report injection.<br/>• **Scenario Presets:** Instant loading of the 4 Judge Rubric Scenarios (Network Outage, Smoke/Electrical, Contractor Check, Lift/Accessibility) plus Unseen CSV Upload.<br/>• **Submission Artifacts:** `architecture.md`, `team_declaration.md`, `README.md`, and one-line setup/run scripts (`run.bat`, `run.sh`, `run_predictions.py`). |

---

## 2. Statement of Originality & Borrowed Components

1. **Original Work:** All correlation heuristics, decision trees, state machines, UI components, and replay loops were authored by this team.
2. **Borrowed Libraries & Frameworks:**
   - `streamlit` (Apache 2.0) — Frontend dashboard presentation and reactive state management.
   - `plotly` (MIT License) — Interactive cognitive evolution and category distribution charts.
   - `pandas` (BSD-3-Clause) — Tabular presentation and CSV export formatting.
   - `pydantic` (MIT License) — Strict schema validation ensuring 100% adherence to JSONL predictions contract.
3. **External Services / APIs:** Zero hard-coded proprietary API dependencies; runs fully self-contained offline for reproducible evaluation.

---

## 3. Human-in-the-Loop & Safety Affirmation

- The system identifies contradictory incoming accounts (`relationship: CONFLICT`) and automatically triggers `human_review: true` to prevent hallucinated consensus.
- Life-safety and high-consequence reports from non-authoritative sources are flagged for human supervisor confirmation before irreversible physical actions are triggered.
- Deduplication prevents responder fatigue by distinguishing fresh dispatches (`DISPATCH`) from ongoing response maintenance (`CONTINUE_RESPONSE`).

---

**Signed on behalf of Team Divitiae Tech:**  
*Member 1 (Core Agent & Correlation Logic)*  
*Member 2 (Decision Engine & Prediction Exporter)*  
*Member 3 (Dashboard, Replay & Documentation)*  
*September 16, 2026*
