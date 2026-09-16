"""Member 2: Assess -> Decide -> Act -> Record on top of Member 1's tracker.

Consumes one `CorrelationResult` (report + incident + clustering
relationship) at a time, in file order, and produces a schema-valid
prediction plus a human-readable reason for the dashboard.

Safety rules enforced here:
- a service is engaged (DISPATCH / REQUEST_* / CREATE_TICKET / NOTIFY) at
  most once per incident; later evidence gets CONTINUE_RESPONSE, and
  duplicates or already-handled evidence get [];
- hedged/contradicting evidence becomes relationship=CONFLICT, never
  silently downgrades severity, asks for verification and sets
  human_review=true;
- critical risk, low confidence, unmapped reports, reopenings and closure
  of a formerly critical incident are flagged for human review;
- an incident is only closed on explicit resolution evidence, and a
  resolved incident reopens if new non-resolution evidence arrives.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import signals
from schema import PREDICTION_KEYS, validate_prediction
from services import (SEVERITY_ORDER, ServiceDirectory, engagement_action, normalise_category,
                      required_services, sev_rank)

LOW_CONFIDENCE = 0.5


@dataclass
class IncidentState:
    incident_id: str
    category: Optional[str]
    location: str
    severity: str = "MEDIUM"
    peak_severity: str = "MEDIUM"
    status: str = "INVESTIGATING"
    confidence: float = 0.6
    # logical service id -> (resolved service id, action type that engaged it)
    engaged: Dict[str, tuple] = field(default_factory=dict)
    primary_service: Optional[str] = None
    report_ids: List[str] = field(default_factory=list)
    sources: set = field(default_factory=set)
    conflicts: int = 0
    closed_once: bool = False
    action_history: List[dict] = field(default_factory=list)


@dataclass
class Decision:
    prediction: dict
    reason: str
    category: Optional[str]
    location: str
    report_description: str
    incident_snapshot: dict


def _clamp(x: float, lo: float = 0.05, hi: float = 0.95) -> float:
    return max(lo, min(hi, x))


def _max_sev(*sevs) -> Optional[str]:
    ranked = [s for s in sevs if sev_rank(s) >= 0]
    return max(ranked, key=sev_rank) if ranked else None


class DecisionEngine:
    def __init__(self, directory: ServiceDirectory):
        self.directory = directory
        self.states: Dict[str, IncidentState] = {}

    # ------------------------------------------------------------------ API

    def decide(self, correlation) -> Decision:
        report = correlation.report
        incident = correlation.incident
        text = signals.normalize(report.description)
        location_norm = signals.normalize(report.location or incident.location)
        reported = report.reported_severity if report.reported_severity in SEVERITY_ORDER else None
        evidence = signals.evidence_severity(text)
        verified_source = report.reporter_type in signals.VERIFIED_SOURCES

        state = self.states.get(incident.incident_id)
        is_new = state is None or correlation.relationship == "NEW"
        category = normalise_category(report.category, text)
        reasons: List[str] = []
        review_reasons: List[str] = []

        if is_new:
            state = IncidentState(incident_id=incident.incident_id, category=category,
                                  location=report.location or incident.location)
            self.states[incident.incident_id] = state
        elif state.category is None and category:
            state.category = category
        if not state.location and report.location:
            state.location = report.location

        prev_status, prev_severity = state.status, state.severity

        relationship = self._relationship(correlation, state, text, is_new)
        severity = self._assess_severity(state, relationship, reported, evidence, text, is_new,
                                         reasons, review_reasons)
        status = self._assess_status(state, relationship, severity, text, is_new, reasons, review_reasons)
        if status in ("ACTIVE", "ESCALATED") and prev_status == "RESOLVED" and relationship == "RESOLUTION":
            relationship = "UPDATE"
        if prev_status == "RESOLVED" and status != "RESOLVED" and relationship in ("DUPLICATE", "RESOLUTION"):
            relationship = "UPDATE"

        confidence = self._assess_confidence(state, correlation, relationship, report, verified_source,
                                             is_new, text)
        actions = self._choose_actions(state, relationship, severity, status, prev_status,
                                       prev_severity, text, location_norm, report, reasons)

        # ---- human review ----
        if relationship == "CONFLICT" or (is_new and signals.is_conflict(text)):
            review_reasons.append("conflicting or uncertain evidence")
        if confidence < LOW_CONFIDENCE:
            review_reasons.append(f"low confidence {confidence:.2f}")
        if state.category is None:
            review_reasons.append("could not map report to a service type")
        if severity == "CRITICAL" and (is_new or prev_severity != "CRITICAL") and status != "RESOLVED":
            review_reasons.append("critical risk")
        if status == "RESOLVED" and prev_status != "RESOLVED" and state.peak_severity == "CRITICAL":
            review_reasons.append("closing an incident that was critical")
        if (state.category == "security" and any(a["type"] == "DISPATCH" for a in actions)
                and any(w in text for w in ("person", "someone", "figure", "contractor", "student"))):
            review_reasons.append("security response involving an identified person")
        human_review = bool(review_reasons)

        # ---- record ----
        state.severity = severity
        state.peak_severity = _max_sev(state.peak_severity, severity)
        state.status = status
        state.confidence = confidence
        state.report_ids.append(report.report_id)
        if report.reporter_type:
            state.sources.add(report.reporter_type)
        for action in actions:
            state.action_history.append({
                "report_id": report.report_id, "timestamp": report.raw_timestamp,
                "type": action["type"], "service_id": action["service_id"],
                "new_action": action["type"] not in ("CONTINUE_RESPONSE", "MONITOR", "NO_NEW_ACTION"),
                "status": status,
            })

        prediction = {
            "report_id": report.report_id,
            "incident_id": incident.incident_id,
            "relationship": relationship,
            "severity": severity,
            "confidence": round(confidence, 2),
            "actions": actions,
            "incident_status": status,
            "human_review": human_review,
        }
        validate_prediction(prediction, self.directory.ids)

        if not actions:
            reasons.append("no new action: existing response sufficient")
        if review_reasons:
            reasons.append("human review: " + ", ".join(dict.fromkeys(review_reasons)))
        reason = f"{relationship.lower()} evidence; " + "; ".join(dict.fromkeys(reasons))

        return Decision(
            prediction=prediction, reason=reason, category=state.category, location=state.location,
            report_description=report.description,
            incident_snapshot={
                "incident_id": state.incident_id, "category": state.category, "location": state.location,
                "severity": severity, "peak_severity": state.peak_severity, "status": status,
                "confidence": round(confidence, 2), "report_ids": list(state.report_ids),
                "services": sorted({svc for svc, _ in state.engaged.values()}),
                "conflicts": state.conflicts,
            },
        )

    @staticmethod
    def fallback_prediction(report_id: str, incident_id: str, relationship: str) -> dict:
        """Used by the pipeline if a decision raises: still one valid line
        per report, flagged for a human instead of guessing."""
        return dict(zip(PREDICTION_KEYS, (
            report_id, incident_id or "I999",
            relationship if relationship in ("NEW", "UPDATE", "CORROBORATION", "CONFLICT",
                                             "DUPLICATE", "RESOLUTION") else "UPDATE",
            "MEDIUM", 0.3, [], "INVESTIGATING", True,
        )))

    # ---------------------------------------------------------- relationship

    def _relationship(self, correlation, state, text, is_new) -> str:
        if is_new:
            return "NEW"
        if signals.is_explicit_duplicate(text):
            return "DUPLICATE"
        if signals.is_resolution(text):
            return "RESOLUTION"
        if signals.is_conflict(text) or correlation.conflict_candidate:
            return "CONFLICT"
        if correlation.relationship == "DUPLICATE":
            return "DUPLICATE"
        if correlation.relationship in ("UPDATE", "CORROBORATION"):
            return correlation.relationship
        return "UPDATE"

    # -------------------------------------------------------------- severity

    def _assess_severity(self, state, relationship, reported, evidence, text, is_new,
                         reasons, review_reasons) -> str:
        # Reporter severity is not ground truth: an unsupported CRITICAL is
        # capped at HIGH (and flagged) until the description backs it up.
        claimed = reported
        if reported == "CRITICAL" and evidence != "CRITICAL":
            claimed = "HIGH"
            if is_new:
                review_reasons.append("reported CRITICAL without supporting evidence")
        candidate = _max_sev(claimed, evidence)

        if is_new:
            severity = candidate or "MEDIUM"
            reasons.append(f"severity {severity} from "
                           f"{'description evidence' if evidence and sev_rank(evidence) >= sev_rank(claimed) else 'reported value' if claimed else 'default (no severity evidence)'}")
            return severity

        current = state.severity
        if relationship in ("DUPLICATE", "CONFLICT"):
            if relationship == "CONFLICT" and candidate and sev_rank(candidate) < sev_rank(current):
                reasons.append(f"kept severity {current} despite hedged evidence")
            return current
        if relationship == "RESOLUTION":
            return "LOW"

        if candidate and sev_rank(candidate) > sev_rank(current):
            reasons.append(f"severity escalated {current}->{candidate}")
            return candidate

        worsening = signals.is_worsening(text)
        controlled = state.status in ("CONTROLLED", "RESOLVED") or signals.is_control(text)
        if candidate and sev_rank(candidate) < sev_rank(current) and controlled and not worsening:
            # De-escalate gradually, never below what the new report supports.
            stepped = SEVERITY_ORDER[max(sev_rank(candidate), sev_rank(current) - 1)]
            reasons.append(f"severity de-escalated {current}->{stepped} as situation is controlled")
            return stepped

        # Several weak signals collectively justify escalation.
        if current == "LOW" and len(state.report_ids) + 1 >= 4 and state.status not in ("CONTROLLED", "RESOLVED"):
            reasons.append("severity raised LOW->MEDIUM: repeated reports")
            return "MEDIUM"
        return current

    # ---------------------------------------------------------------- status

    def _assess_status(self, state, relationship, severity, text, is_new, reasons, review_reasons) -> str:
        worsening = signals.is_worsening(text)
        if is_new:
            if severity == "CRITICAL":
                return "ESCALATED"
            return "ACTIVE" if severity == "HIGH" else "INVESTIGATING"

        current = state.status
        if relationship == "RESOLUTION":
            if current != "RESOLVED":
                reasons.append("explicit resolution evidence: closing incident")
            return "RESOLVED"

        if current == "RESOLVED":
            if relationship == "DUPLICATE" or signals.is_control(text) or not (
                    worsening or signals.evidence_severity(text)):
                return "RESOLVED"
            reasons.append("new hazard evidence after resolution: reopening incident")
            review_reasons.append("incident reopened")
            return "ESCALATED" if severity == "CRITICAL" else "ACTIVE"

        if relationship in ("DUPLICATE", "CONFLICT"):
            if current == "INVESTIGATING" and relationship == "DUPLICATE":
                reasons.append("independent repeat reports: incident now active")
                return "ACTIVE"
            return current

        if worsening and current == "CONTROLLED":
            reasons.append("situation worsening again: control lost")
            return "ESCALATED" if severity == "CRITICAL" else "ACTIVE"

        if signals.is_control(text) and not worsening:
            if current != "CONTROLLED":
                reasons.append("response reports the hazard is contained")
            return "CONTROLLED"

        if current == "CONTROLLED":
            return "CONTROLLED"
        if severity == "CRITICAL":
            if current != "ESCALATED":
                reasons.append("critical evidence: escalating")
            return "ESCALATED"
        if current == "ESCALATED":
            return "ESCALATED"
        return "ACTIVE"

    # ------------------------------------------------------------ confidence

    def _assess_confidence(self, state, correlation, relationship, report, verified_source, is_new, text) -> float:
        if is_new:
            conf = 0.6 + (0.1 if verified_source else 0.0)
            missing = sum(1 for v in (report.location, report.category, report.description) if not v)
            conf -= 0.15 * missing
            if report.timestamp is None:
                conf -= 0.05
            if not text:
                conf -= 0.1
            return _clamp(conf)

        conf = state.confidence
        new_source = report.reporter_type and report.reporter_type not in state.sources
        if relationship == "CONFLICT":
            state.conflicts += 1
            conf -= 0.15
        elif relationship == "RESOLUTION":
            conf = max(conf, 0.85 if verified_source else 0.75)
        elif relationship == "DUPLICATE":
            conf += 0.02
        else:
            conf += 0.05 + (0.03 if new_source else 0.0) + (0.02 if verified_source else 0.0)
            if state.conflicts and verified_source and signals.is_control(text):
                # Official responders on scene settle earlier disagreement.
                conf += 0.05
        # A weak clustering match makes this report's evidence less reliable
        # for this incident.
        if correlation.confidence < 0.6:
            conf -= 0.05
        return _clamp(conf)

    # --------------------------------------------------------------- actions

    def _engage(self, state, logical_id, severity, text, report, actions, reasons, action_type=None):
        # A date-only timestamp says nothing about office hours.
        at = report.timestamp if ":" in (report.raw_timestamp or "") else None
        resolved = self.directory.resolve(logical_id, at)
        already = any(svc == resolved for lid, (svc, _) in state.engaged.items() if lid != logical_id)
        action_type = action_type or engagement_action(resolved, severity, text)
        state.engaged[logical_id] = (resolved, action_type)
        if already:
            # Fallback landed on a service this incident already engaged.
            return
        if state.primary_service is None and action_type != "NOTIFY":
            state.primary_service = resolved
        if resolved != logical_id:
            reasons.append(f"{logical_id} unavailable at this time, using {resolved}")
        actions.append({"type": action_type, "service_id": resolved})

    def _choose_actions(self, state, relationship, severity, status, prev_status, prev_severity,
                        text, location_norm, report, reasons) -> List[dict]:
        actions: List[dict] = []
        primary = state.primary_service

        if relationship == "DUPLICATE":
            reasons.append("duplicate: no repeat dispatch")
            return actions

        if relationship == "RESOLUTION":
            if prev_status != "RESOLVED":
                actions.append({"type": "CLOSE_INCIDENT", "service_id": primary or "SVC-MANAGEMENT"})
            return actions

        if relationship == "CONFLICT":
            target = primary or self.directory.resolve(
                required_services(state.category, text, severity, location_norm)[0], report.timestamp)
            actions.append({"type": "REQUEST_VERIFICATION", "service_id": target})
            reasons.append("requesting verification of conflicting account")
            if primary and sev_rank(severity) >= sev_rank("HIGH") and status not in ("CONTROLLED", "RESOLVED"):
                actions.append({"type": "CONTINUE_RESPONSE", "service_id": primary})
                reasons.append("response maintained until verified")
            return actions

        reopened = prev_status == "RESOLVED" and status != "RESOLVED"
        if status in ("CONTROLLED", "RESOLVED"):
            if status == "CONTROLLED" and prev_status != "CONTROLLED" and primary:
                actions.append({"type": "MONITOR", "service_id": primary})
            return actions

        needed = required_services(state.category, text, severity, location_norm)
        # A first report that already hedges ("alarm test", "may only be")
        # gets verified before anyone is sent, unless it is critical.
        verify_first = (not state.report_ids and severity != "CRITICAL" and signals.is_conflict(text))
        for logical_id in needed:
            if logical_id not in state.engaged:
                self._engage(state, logical_id, severity, text, report, actions, reasons,
                             action_type="REQUEST_VERIFICATION" if verify_first and logical_id == needed[0] else None)
            elif (state.engaged[logical_id][1] == "REQUEST_VERIFICATION"
                  and engagement_action(state.engaged[logical_id][0], severity, text) == "DISPATCH"):
                # Verification has turned into a confirmed need: dispatch once.
                self._engage(state, logical_id, severity, text, report, actions, reasons, action_type="DISPATCH")
            elif reopened:
                actions.append({"type": "DISPATCH" if logical_id != "SVC-MANAGEMENT" else "NOTIFY",
                                "service_id": self.directory.resolve(logical_id, report.timestamp)})
        if actions:
            reasons.append("engaging " + ", ".join(f"{a['type']} {a['service_id']}" for a in actions))

        primary = state.primary_service
        escalated_now = (sev_rank(severity) > sev_rank(prev_severity) and severity == "CRITICAL"
                         and prev_status in ("INVESTIGATING", "ACTIVE") and primary)
        if escalated_now and not any(a["service_id"] == primary and a["type"] == "DISPATCH" for a in actions):
            actions.append({"type": "ESCALATE_RESPONSE", "service_id": primary})
            reasons.append(f"escalating {primary} response")

        if not actions and primary:
            actions.append({"type": "CONTINUE_RESPONSE", "service_id": primary})
            reasons.append(f"{primary} already engaged: continuing, no repeat dispatch")
        return actions
