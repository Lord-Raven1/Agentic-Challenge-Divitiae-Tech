"""Incident state memory and report-to-incident correlation.

This is the Member 1 handoff surface: feed reports one at a time, in file
order, and get back which incident each belongs to and how it relates to
that incident's existing evidence. Member 2's decision engine consumes
CorrelationResult to pick severity/actions/status; this module only owns
clustering + raw incident memory.
"""
import itertools
from typing import List, Optional

from models import CorrelationResult, Incident, Report
from conflict_llm import suggests_conflict_gemini, suggests_conflict_qwen
from matching import similarity, suggests_conflict, text_similarity

STRONG_MATCH_THRESHOLD = 0.75
WEAK_MATCH_THRESHOLD = 0.45

DUPLICATE_TEXT_SIMILARITY = 0.9


class IncidentTracker:
    def __init__(self):
        self._incidents: dict[str, Incident] = {}
        self._id_counter = itertools.count(1)

    @property
    def incidents(self) -> List[Incident]:
        return list(self._incidents.values())

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        return self._incidents.get(incident_id)

    def process(self, report: Report) -> CorrelationResult:
        best_incident, best_score = self._find_best_match(report)

        if best_incident is None or best_score < WEAK_MATCH_THRESHOLD:
            incident = self._create_incident(report)
            self._apply(incident, report)
            return CorrelationResult(report=report, incident=incident,
                                      relationship="NEW", confidence=0.9,
                                      conflict_candidate=False)

        relationship = self._classify_relationship(report, best_incident, best_score)
        # Only meaningful once there is prior evidence to hedge against or
        # contradict; a fresh incident's first report can't yet conflict.
        conflict_candidate = False
        if relationship != "DUPLICATE":
            conflict_candidate = self._check_conflict(report, best_incident)
        self._apply(best_incident, report)
        return CorrelationResult(report=report, incident=best_incident,
                                  relationship=relationship, confidence=round(best_score, 2),
                                  conflict_candidate=conflict_candidate)

    def _check_conflict(self, report: Report, incident: Incident) -> bool:
        """Fallback order: Gemini -> keyword heuristic -> local Qwen. This is
        accuracy order for the first two, then Qwen last — not because it's
        least accurate (though it is), but because the keyword heuristic
        needs no external service and always works, while Qwen needs Ollama
        running locally and can't be assumed available wherever this
        actually gets submitted/run. See conflict_llm.py for the measured
        recall numbers behind this ordering."""
        verdict = suggests_conflict_gemini(report.description, incident.last_description)
        if verdict is not None:
            return verdict

        try:
            return suggests_conflict(report.description)
        except Exception:
            pass

        verdict = suggests_conflict_qwen(report.description, incident.last_description)
        return bool(verdict)

    def _find_best_match(self, report: Report):
        best_incident, best_score = None, 0.0
        for incident in self._incidents.values():
            score = similarity(
                report,
                incident_location=incident.location,
                incident_category=incident.category,
                incident_last_timestamp=incident.last_timestamp,
                incident_description=incident.last_description,
                report_timestamp=report.timestamp,
            )
            if score is not None and score > best_score:
                best_incident, best_score = incident, score
        return best_incident, best_score

    def _classify_relationship(self, report: Report, incident: Incident, score: float) -> str:
        # Near-identical wording to *any* prior report on this incident is a
        # duplicate submission regardless of who sent it or how long ago —
        # e.g. the same complaint resubmitted 20 minutes later is still a
        # duplicate, not a fresh update.
        max_desc_sim = max(
            (text_similarity(report.description, prior) for prior in incident.descriptions),
            default=0.0,
        )
        if max_desc_sim >= DUPLICATE_TEXT_SIMILARITY:
            return "DUPLICATE"

        if score < STRONG_MATCH_THRESHOLD:
            # Same incident, but weak enough evidence that it reads as
            # corroborating detail rather than a direct update.
            return "CORROBORATION"

        same_source = report.reporter_type in incident.reporter_types
        if not same_source and incident.reporter_types:
            return "CORROBORATION"

        return "UPDATE"

    def _create_incident(self, report: Report) -> Incident:
        incident_id = f"I{next(self._id_counter):03d}"
        return Incident(
            incident_id=incident_id,
            location=report.location,
            category=report.category,
            severity=report.reported_severity or "LOW",
        )

    def _apply(self, incident: Incident, report: Report) -> None:
        incident.report_ids.append(report.report_id)
        incident.reporter_types.add(report.reporter_type)
        incident.last_description = report.description
        incident.descriptions.append(report.description)
        if report.timestamp:
            incident.last_timestamp = report.timestamp
        # Track the highest severity seen; Member 2's decision engine may
        # override this with rule-based logic downstream.
        if _severity_rank(report.reported_severity) > _severity_rank(incident.severity):
            incident.severity = report.reported_severity
        self._incidents[incident.incident_id] = incident


_SEVERITY_ORDER = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def _severity_rank(severity: str) -> int:
    try:
        return _SEVERITY_ORDER.index((severity or "LOW").upper())
    except ValueError:
        return 0
