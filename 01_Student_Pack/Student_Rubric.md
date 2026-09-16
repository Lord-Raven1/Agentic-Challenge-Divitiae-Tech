# Campus Crisis Agent
## Student Assessment and Rubric Guide

**STUDENT-FACING**

### Final score

| Component | Marks |
|---|---:|
| Automated behavioural evaluation | 60 |
| Human dashboard/agent evaluation | 25 |
| Technical defence | 15 |
| **Total** | **100** |

### A. Automated behavioural evaluation - 60

| Criterion | Marks | What earns credit |
|---|---:|---|
| Incident correlation | 15 | Related reports share an incident; unrelated reports remain separate. Pairwise precision, recall and F1 are used. |
| Action/service selection | 12 | Required responses are selected, acceptable alternatives are allowed and inappropriate responses are avoided. |
| Severity/prioritisation | 8 | Severity reflects the evidence and changes as the situation changes. |
| State/lifecycle progression | 8 | Incident status is reasonable for the evidence available at that point. |
| Changing/conflicting evidence | 7 | The agent identifies conflict, updates its view and does not hide uncertainty. |
| Duplicate-action avoidance | 4 | Duplicate reports do not cause unnecessary new dispatches. |
| Safety | 4 | The agent avoids forbidden actions and requests human review where required. |
| Resolution/closure | 2 | Closure is supported by evidence and is not premature. |

### B. Human dashboard/agent evaluation - 25

| Criterion | Marks |
|---|---:|
| Reasoning is understandable and traceable | 5 |
| Evolving context meaningfully affects decisions | 5 |
| Decisions are coherent and defensible | 5 |
| Uncertainty and conflicting evidence are handled intelligently | 4 |
| Human oversight is used appropriately | 3 |
| Dashboard makes behaviour easy to inspect | 3 |

Judges replay the same four scenarios for every team: network outage, smoke/electrical incident, contractor verification and lift/accessibility incident.

### C. Technical defence - 15

| Criterion | Marks |
|---|---:|
| Architecture understanding | 4 |
| Agentic design understanding | 4 |
| Implementation understanding | 3 |
| Limitations and testing awareness | 2 |
| Evidence of team ownership and contribution | 2 |

### Selection

The five highest-scoring eligible teams are selected intact. Ties are broken by automated score, then safety, incident correlation, human evaluation and technical defence. A submission must run, produce predictions for at least 80% of unseen reports and complete the defence to remain eligible.
