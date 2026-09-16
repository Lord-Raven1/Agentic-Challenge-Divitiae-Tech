# Campus Crisis Agent
## Technical and Submission Guide

**STUDENT-FACING**

### Input CSV

Each row contains: `report_id`, `timestamp`, `location`, `category`, `reported_severity`, `description`, `reporter_type`.

Treat all fields except `report_id` as potentially missing or inconsistent. Process reports in file order. Do not reorder by timestamp because an unseen timestamp may be malformed.

### Required JSONL prediction

Write exactly one JSON object per processed report:

```json
{
  "report_id": "R104",
  "incident_id": "I003",
  "relationship": "CORROBORATION",
  "severity": "CRITICAL",
  "confidence": 0.92,
  "actions": [{"type": "CONTINUE_RESPONSE", "service_id": "SVC-FIRE"}],
  "incident_status": "ESCALATED",
  "human_review": false
}
```

Required values:

- `relationship`: `NEW`, `UPDATE`, `CORROBORATION`, `CONFLICT`, `DUPLICATE` or `RESOLUTION`.
- `severity`: `LOW`, `MEDIUM`, `HIGH` or `CRITICAL`.
- `confidence`: number from 0 to 1.
- `incident_status`: `INVESTIGATING`, `ACTIVE`, `ESCALATED`, `CONTROLLED` or `RESOLVED`.
- `human_review`: Boolean.
- `actions`: an array; `[]` is valid and means no new action.

Recommended action types: `DISPATCH`, `NOTIFY`, `REQUEST_INSPECTION`, `REQUEST_VERIFICATION`, `ESCALATE_RESPONSE`, `CONTINUE_RESPONSE`, `CREATE_TICKET`, `MONITOR`, `CLOSE_INCIDENT`, `NO_NEW_ACTION`.

`CONTINUE_RESPONSE` means an existing response remains appropriate. It should not represent another dispatch.

### Dashboard acceptance checklist

- Current input report is visible.
- Every processed report appears in a decision log.
- Clicking an incident reveals its reports and current assessment.
- Action history distinguishes new actions from continued actions.
- Conflicting evidence and confidence changes can be found quickly.
- The dashboard can replay reports in supplied order.

### Submission structure

```text
team-name/
  README.md
  architecture.md
  source/
  prompts/              # if used
  package or dependency files
  run_predictions.*
  team_declaration.md
```

The README must state one exact command for setup, one for running the dashboard and one for generating predictions. Do not include secrets. Provide required environment-variable names separately.

### Freeze checklist

- Run the system from a clean start.
- Confirm output is valid JSONL with one line per report.
- Confirm report IDs match the input.
- Confirm the dashboard displays the same decisions as the JSONL output.
- Remove API keys and personal data.
- Submit before the announced freeze time.
