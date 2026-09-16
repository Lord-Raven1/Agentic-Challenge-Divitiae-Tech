"""
Data Models for Campus Crisis Agent.
Defines schemas for Incoming Reports, Agent Decisions, Incident State, Actions, and Replay Ticks.
Strictly conforms to the Technical and Submission Guide JSONL contract.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    """An action dispatched or maintained by the agent."""
    type: str  # DISPATCH, NOTIFY, REQUEST_INSPECTION, REQUEST_VERIFICATION, ESCALATE_RESPONSE, CONTINUE_RESPONSE, CREATE_TICKET, MONITOR, CLOSE_INCIDENT, NO_NEW_ACTION
    service_id: str  # e.g., SVC-FIRE, SVC-IT, SVC-SECURITY, etc.


class CampusReport(BaseModel):
    """Raw report evidence row from campus_reports.csv or test CSV."""
    report_id: str
    timestamp: str = ""
    location: str = ""
    category: str = ""
    reported_severity: str = "MEDIUM"
    description: str = ""
    reporter_type: str = ""
    
    # Data hygiene flags
    missing_fields: List[str] = Field(default_factory=list)
    is_timestamp_malformed: bool = False
    clean_location: str = ""
    clean_category: str = ""


class PredictionOutput(BaseModel):
    """Strict JSONL contract required by Technical & Submission Guide."""
    report_id: str
    incident_id: str
    relationship: str  # NEW, UPDATE, CORROBORATION, CONFLICT, DUPLICATE, RESOLUTION
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    confidence: float = Field(..., ge=0.0, le=1.0)
    actions: List[ActionItem] = Field(default_factory=list)
    incident_status: str  # INVESTIGATING, ACTIVE, ESCALATED, CONTROLLED, RESOLVED
    human_review: bool


class DecisionLogEntry(BaseModel):
    """Decision log entry capturing agent deliberation and concise reasoning."""
    report_id: str
    incident_id: str
    relationship: str
    severity: str
    confidence: float
    actions: List[ActionItem] = Field(default_factory=list)
    decision: str  # Primary decision summary (e.g., "DISPATCH SVC-FIRE", "CONTINUE_RESPONSE", "ESCALATE")
    service: str   # Primary service ID(s)
    status: str    # Incident status (INVESTIGATING, ACTIVE, ESCALATED, etc.)
    concise_reason: str  # Traceable explanation for judges
    human_review: bool = False
    conflict_detected: bool = False
    confidence_delta: float = 0.0  # Change relative to previous tick for this incident


class ActionHistoryItem(BaseModel):
    """Action history record for an incident."""
    action_id: str
    incident_id: str
    report_id: str
    time: str
    action_type: str  # e.g., DISPATCH, CONTINUE_RESPONSE, NOTIFY
    service_id: str
    service_name: str
    is_new_action: bool  # True if new dispatch/action; False if CONTINUE_RESPONSE / unchanged
    outcome_status: str  # e.g., "DISPATCHED", "MAINTAINED", "ESCALATED", "COMPLETED", "MONITORING"
    notes: str = ""


class IncidentSnapshot(BaseModel):
    """Incident state snapshot as required by View 3 (Incident Summary)."""
    incident_id: str
    current_type: str        # e.g. "fire", "it", "accessibility", "security"
    location: str            # e.g. "Engineering Block E3"
    severity: str            # LOW, MEDIUM, HIGH, CRITICAL
    confidence: float        # 0.0 - 1.0
    report_ids: List[str]    # List of correlated report IDs
    reports_count: int = 0
    services: List[str]      # Assigned/dispatched services
    status: str              # INVESTIGATING, ACTIVE, ESCALATED, CONTROLLED, RESOLVED
    action: str              # Latest action taken
    human_review: bool = False
    evolving_assessment: str # Synthesis of situation based on all evidence so far
    reports_history: List[CampusReport] = Field(default_factory=list)
    severity_progression: List[str] = Field(default_factory=list)
    confidence_progression: List[float] = Field(default_factory=list)


class ReplayTick(BaseModel):
    """Single tick in sequential replay corresponding to processing one report."""
    tick_index: int
    report: CampusReport
    prediction: PredictionOutput
    decision: DecisionLogEntry
    new_actions: List[ActionHistoryItem] = Field(default_factory=list)
    all_actions_snapshot: List[ActionHistoryItem] = Field(default_factory=list)
    incident_states: Dict[str, IncidentSnapshot] = Field(default_factory=dict)
    active_incident_id: str
    narrative: str = ""


class CampusScenario(BaseModel):
    """Complete multi-tick scenario for replay."""
    scenario_id: str
    title: str
    description: str
    badge: str
    total_ticks: int
    ticks: List[ReplayTick] = Field(default_factory=list)


class CampusService(BaseModel):
    """Fictional campus service entry from campus_services.csv."""
    service_id: str
    service_name: str
    service_type: str
    availability: str
    scope: str
