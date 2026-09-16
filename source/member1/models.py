from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Report:
    report_id: str
    row_index: int
    raw_timestamp: str
    timestamp: Optional[datetime]
    location: str
    category: str
    reported_severity: str
    description: str
    reporter_type: str


@dataclass
class Incident:
    incident_id: str
    location: str
    category: str
    status: str = "INVESTIGATING"
    severity: str = "LOW"
    confidence: float = 0.5
    services_dispatched: set = field(default_factory=set)
    report_ids: list = field(default_factory=list)
    last_timestamp: Optional[datetime] = None
    last_description: str = ""
    descriptions: list = field(default_factory=list)
    reporter_types: set = field(default_factory=set)


@dataclass
class CorrelationResult:
    report: Report
    incident: Incident
    relationship: str
    confidence: float
    # True when this report's wording hedges or contradicts prior evidence
    # on the same incident (e.g. "may only be a false alarm"). A correlation-
    # layer heuristic only — Member 2's decision engine owns the final call
    # on whether to surface this as relationship=CONFLICT.
    conflict_candidate: bool = False
