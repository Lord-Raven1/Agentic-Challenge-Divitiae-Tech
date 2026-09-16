"""Keyword evidence extracted from free-text report descriptions.

The reporter-supplied category and severity are explicitly *not* ground
truth, so the decision engine leans on what the description actually says.
Phrases are matched on normalised lowercase text; keep them specific enough
that ordinary status updates don't trip them.
"""
import re

from rapidfuzz import fuzz

_WORD_RE = re.compile(r"[a-z0-9']+")


def normalize(text: str) -> str:
    return " ".join(_WORD_RE.findall((text or "").lower()))


def _has_any(text: str, phrases) -> bool:
    padded = f" {text} "
    return any(f" {p} " in padded for p in phrases)


# --- Life/safety escalation -------------------------------------------------
CRITICAL_PHRASES = [
    "lost consciousness", "unconscious", "not breathing", "unresponsive", "found dead",
    "cardiac", "seizure", "severe bleeding", "overdose", "sparks", "flames", "on fire",
    "fire in", "explosion", "gas leak", "alarm has activated", "fire alarm has been triggered",
    "trapped", "occupants inside", "stopped between floors", "asks students to leave",
    "evacuat", "weapon", "armed", "lockdown", "security breach", "hostage", "external emergency medical",
    "immediate medical attention", "found missing",
]
HIGH_PHRASES = [
    "smoke", "burning", "collapsed", "collapse", "exposed wiring", "unsafe", "hot", "buzzing", "restricted",
    "trying keys", "confused", "breathing quickly", "fainting", "injur", "flood",
    "multiple buildings", "campus wide", "no equivalent accessible route", "wheelchair",
    "power extension", "failed logins", "dark section", "lost power", "suspicious",
    "smoke detector", "fire alarm", "leak", "sprinkler",
]
# "Again" / spreading language re-escalates an incident that looked controlled.
WORSENING_PHRASES = [
    "again", "spread", "spreading", "worse", "worsening", "becoming unsafe", "reached",
    "now show", "failing again", "re ignited", "reignited", "still burning", "more smoke",
]

# --- Uncertainty / conflict -------------------------------------------------
CONFLICT_PHRASES = [
    "may only be", "may be dust", "thinks it is only", "unconfirmed", "not yet confirmed",
    "not confirmed", "false alarm", "no evidence", "may not be", "believes it is only",
    "believes the issue is local", "cannot confirm", "disputes", "contradicts", "conflicts with",
    "mistaken", "turns out", "was not actually", "may have been scheduled", "still passable",
    "briefly returned", "doors are open", "only a test", "alarm test", "drill",
]

# --- Lifecycle ----------------------------------------------------------------
RESOLUTION_PHRASES = [
    "resolved", "returned to service", "reopened", "entrance reopens", "passes the safety test",
    "no remaining", "services are stable",
    "stood down", "power restored", "connectivity is restored", "all clear", "incident closed",
    "back to normal", "fully restored",
]
# Explicitly "controlled" rather than closed (e.g. "Controlled: medical handover").
CONTROL_PHRASES = [
    "controlled", "isolated", "isolate", "cordoned", "barrier", "flow has stopped",
    "released safely", "temperature is falling", "buzzing stops", "temporary lighting",
    "temporary route restores", "most users can connect", "most glass has been removed",
    "responsive and being monitored", "verified", "handover", "no additional water",
    "no new failures", "normal traffic", "dry and accessible", "departed with the student",
    "replaces the failed", "is replaced",
    "remains stable", "under test", "no further assistance is required", "removes the temporary", "final sweep", "no wider hazard",
    "no forced entry", "extracting water", "removing the glass", "repairs are complete",
    "has been removed and inspected", "court is clear", "alternative route is active",
]
# "Still unavailable", "remains closed" etc. keep an incident open even if it
# also mentions a control phrase.
STILL_OPEN_PHRASES = [
    "remains unavailable", "still degraded", "remain unstable", "remains closed pending",
    "remains hot", "not yet", "still", "remains wet",
]

DUPLICATE_PREFIXES = ("duplicate report", "same as earlier", "repeat report")

VERIFIED_SOURCES = {"security", "staff", "system_sensor"}


def is_explicit_duplicate(text: str) -> bool:
    return text.startswith(DUPLICATE_PREFIXES)


def is_resolution(text: str) -> bool:
    if text.startswith("controlled"):
        return False
    if text.startswith("resolved"):
        return True
    return _has_any(text, RESOLUTION_PHRASES) and not _has_any(text, STILL_OPEN_PHRASES)


def is_control(text: str) -> bool:
    return (text.startswith("controlled") or _has_any(text, CONTROL_PHRASES))


def is_conflict(text: str) -> bool:
    return _has_any(text, CONFLICT_PHRASES) or any(
        p in text for p in ("may only be", "conflicts with", "unconfirmed", "false alarm")
    )


def is_worsening(text: str) -> bool:
    return _has_any(text, WORSENING_PHRASES)


def _prefix_hit(text: str, phrases) -> bool:
    # Prefix-style phrases like "evacuat" / "injur" match word stems.
    padded = f" {text}"
    return any(f" {p}" in padded for p in phrases)


# "not" is deliberately excluded: "not breathing" is itself critical evidence.
_NEGATION_RE = re.compile(r"\b(?:no|without|nobody|none)(?: (?:visible|further|more|sign of|signs of|longer))? \w+")


def evidence_severity(text: str) -> str | None:
    """Severity implied by the description alone; None if nothing stands out."""
    if not text:
        return None
    # "No flames are visible" must not read as "flames".
    text = _NEGATION_RE.sub(" ", text)
    if _prefix_hit(text, CRITICAL_PHRASES):
        return "CRITICAL"
    if _prefix_hit(text, HIGH_PHRASES):
        # Explicitly minor issues ("a minor ankle injury") stay below HIGH.
        return None if " minor " in f" {text} " else "HIGH"
    return None


def fuzzy_contains(text: str, keyword: str, threshold: int = 85) -> bool:
    """Misspelling-tolerant keyword check (e.g. 'smok', 'eletrical')."""
    if keyword in text:
        return True
    return any(fuzz.ratio(word, keyword) >= threshold for word in text.split() if len(word) >= 4)
