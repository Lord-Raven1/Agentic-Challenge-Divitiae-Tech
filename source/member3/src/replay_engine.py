"""
Sequential Report Replay Engine for Campus Crisis Agent.
Maintains stateful, tick-by-tick simulation of reports arriving in file order.
Tracks cumulative decisions, evolving incident assessments, and action history.
"""
from typing import List, Optional, Dict, Any, Set
from src.models import (
    CampusScenario,
    ReplayTick,
    CampusReport,
    DecisionLogEntry,
    ActionHistoryItem,
    IncidentSnapshot,
    PredictionOutput,
)


class ReplayEngine:
    """Manages sequential playback, state accumulation, and live stepping."""

    def __init__(self, scenario: CampusScenario):
        self.scenario = scenario
        self.current_tick_idx: int = 0
        self.is_playing: bool = False
        self.speed_seconds: float = 1.5

    @property
    def total_ticks(self) -> int:
        return len(self.scenario.ticks)

    @property
    def is_finished(self) -> bool:
        return self.current_tick_idx >= self.total_ticks - 1

    def get_current_tick(self) -> ReplayTick:
        """Get the current tick snapshot."""
        if not self.scenario.ticks:
            raise ValueError("Scenario has no ticks.")
        idx = max(0, min(self.current_tick_idx, self.total_ticks - 1))
        return self.scenario.ticks[idx]

    def step_next(self) -> bool:
        """Advance replay by one report."""
        if self.current_tick_idx < self.total_ticks - 1:
            self.current_tick_idx += 1
            return True
        self.is_playing = False
        return False

    def step_prev(self) -> bool:
        """Step back by one report."""
        if self.current_tick_idx > 0:
            self.current_tick_idx -= 1
            return True
        return False

    def step_first(self) -> None:
        """Jump to initial report (Tick 0)."""
        self.current_tick_idx = 0
        self.is_playing = False

    def step_last(self) -> None:
        """Jump to final processed report."""
        self.current_tick_idx = max(0, self.total_ticks - 1)
        self.is_playing = False

    def jump_to_tick(self, idx: int) -> None:
        """Seek directly to report index."""
        self.current_tick_idx = max(0, min(idx, self.total_ticks - 1))

    def reset(self) -> None:
        """Reset replay position to the start."""
        self.current_tick_idx = 0
        self.is_playing = False

    def get_cumulative_reports(self) -> List[CampusReport]:
        """Return all reports received up to current tick."""
        return [self.scenario.ticks[i].report for i in range(self.current_tick_idx + 1)]

    def get_cumulative_decisions(self) -> List[DecisionLogEntry]:
        """Return all decisions made up to current tick."""
        return [self.scenario.ticks[i].decision for i in range(self.current_tick_idx + 1)]

    def get_cumulative_predictions(self) -> List[PredictionOutput]:
        """Return all predictions generated up to current tick."""
        return [self.scenario.ticks[i].prediction for i in range(self.current_tick_idx + 1)]

    def get_cumulative_actions(self) -> List[ActionHistoryItem]:
        """Return full action history up to current tick."""
        current_tick = self.get_current_tick()
        return current_tick.all_actions_snapshot

    def get_incident_states(self) -> Dict[str, IncidentSnapshot]:
        """Return incident state dictionary at current tick."""
        return self.get_current_tick().incident_states

    def get_incident(self, incident_id: str) -> Optional[IncidentSnapshot]:
        """Fetch a specific incident's snapshot at current tick."""
        return self.get_incident_states().get(incident_id)

    def get_conflict_decisions(self) -> List[DecisionLogEntry]:
        """Return all decisions where conflict was detected."""
        return [d for d in self.get_cumulative_decisions() if d.conflict_detected or d.relationship == "CONFLICT"]

    def get_human_review_decisions(self) -> List[DecisionLogEntry]:
        """Return all decisions requiring human oversight."""
        return [d for d in self.get_cumulative_decisions() if d.human_review]

    def get_confidence_drop_decisions(self) -> List[DecisionLogEntry]:
        """Return decisions with significant confidence drops or low confidence."""
        return [d for d in self.get_cumulative_decisions() if d.confidence_delta < 0 or d.confidence < 0.70]
