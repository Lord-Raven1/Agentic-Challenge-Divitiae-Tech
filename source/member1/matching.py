"""Similarity primitives used to correlate reports to incidents.

Uses rapidfuzz for fuzzy text/location matching — it handles the
misspellings and inconsistent labels called out for the unseen test set
far better than a hand-rolled stdlib comparison, at no meaningful cost
(pure C extension, no model download).
"""
import re
from datetime import datetime
from typing import Optional

from rapidfuzz import fuzz

_NUMBER_RE = re.compile(r"\d+")

# Categories that reporters commonly conflate for the same underlying event
# (e.g. an electrical fault reported as "fire" by one person and "electrical"
# by another). Extend as the unseen data surfaces more overlap.
CATEGORY_SYNONYMS = {
    "fire": {"fire", "electrical", "smoke"},
    "electrical": {"electrical", "fire"},
    "medical": {"medical"},
    "security": {"security"},
    "facilities": {"facilities", "environmental"},
    "environmental": {"environmental", "facilities"},
    "it": {"it"},
    "accessibility": {"accessibility"},
}

# A match with a location score below this is rejected outright, regardless
# of how well category/text/time line up — two reports about an unrelated
# location are never the same incident, no matter the topical similarity.
MIN_LOCATION_SCORE = 0.7

# When location is unknown on both sides, category alone is a very weak
# signal (e.g. two unrelated "fire" reports from different buildings would
# otherwise glue together on category match alone). Generic incident
# phrasing also means even unrelated reports often land 0.35-0.55 on text
# similarity, so the bar here has to sit well above that: only near-
# duplicate-level wording is treated as enough evidence to merge when we
# can't verify location at all. A false merge costs correlation precision
# far more than an extra singleton incident costs recall.
MIN_TEXT_SCORE_WHEN_LOCATION_UNKNOWN = 0.7


# Phrases that signal a report is hedging or contradicting prior evidence on
# the same incident, rather than adding a plain factual update. Kept as
# specific multi-word phrases (not a bare "but") since "but" alone appears
# constantly in ordinary status updates (e.g. "no flames, but panel is hot").
CONFLICT_PHRASES = [
    "may only be", "may be dust", "thinks it is only", "unconfirmed",
    "not yet confirmed", "not confirmed", "false alarm", "no evidence",
    "may not be", "believes it is only", "cannot confirm", "disputes",
    "contradicts", "mistaken", "turns out", "was not actually",
]


def suggests_conflict(description: str) -> bool:
    text = normalize_text(description)
    return any(phrase in text for phrase in CONFLICT_PHRASES)


def normalize_text(text: str) -> str:
    return " ".join((text or "").lower().strip().split())


def text_similarity(a: str, b: str) -> float:
    a, b = normalize_text(a), normalize_text(b)
    if not a or not b:
        return 0.0
    return fuzz.token_sort_ratio(a, b) / 100.0


def location_score(a: str, b: str) -> Optional[float]:
    """None means "unknown" (a field was missing) — distinct from 0.0, which
    means both locations are known and clearly different."""
    a, b = normalize_text(a), normalize_text(b)
    if not a or not b:
        return None

    # Fuzzy text scoring alone can't tell "Level 1" from "Level 2" apart —
    # they differ by one character but are different locations. If both
    # sides name numbers and none of those numbers match, it's a distinct
    # location no matter how similar the surrounding text is.
    numbers_a, numbers_b = set(_NUMBER_RE.findall(a)), set(_NUMBER_RE.findall(b))
    if numbers_a and numbers_b and numbers_a.isdisjoint(numbers_b):
        return 0.0

    # partial_ratio rewards one location being a substring/near-substring of
    # the other (e.g. "E3" vs "Engineering Block E3"), while still handling
    # typos gracefully.
    return max(fuzz.ratio(a, b), fuzz.partial_ratio(a, b) * 0.9) / 100.0


def category_score(a: str, b: str) -> float:
    a, b = (a or "").lower(), (b or "").lower()
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if b in CATEGORY_SYNONYMS.get(a, set()):
        return 0.6
    # Catches misspelled/near-miss category labels (e.g. "electricl").
    fuzzy = fuzz.ratio(a, b) / 100.0
    return fuzzy if fuzzy >= 0.85 else 0.0


def time_proximity_score(a: Optional[datetime], b: Optional[datetime], window_minutes: float = 60.0) -> float:
    if a is None or b is None:
        # Missing/malformed timestamps must not silently kill an otherwise
        # strong match on the unseen (dirty) data.
        return 0.5
    delta_minutes = abs((a - b).total_seconds()) / 60.0
    if delta_minutes >= window_minutes:
        return 0.0
    return 1.0 - (delta_minutes / window_minutes)


def similarity(report, incident_location: str, incident_category: str,
               incident_last_timestamp: Optional[datetime], incident_description: str,
               report_timestamp: Optional[datetime]) -> Optional[float]:
    loc = location_score(report.location, incident_location)
    if loc is not None and loc < MIN_LOCATION_SCORE:
        # Hard reject: no amount of category/text/time similarity can paper
        # over a *known*, clearly unrelated location.
        return None

    cat = category_score(report.category, incident_category)
    if report.category and incident_category and cat == 0.0:
        # Hard reject: a shared building hosting an unrelated problem type
        # (e.g. an IT ticket and a security sighting at the same block)
        # is not the same incident just because location matched — a
        # strong location score alone was otherwise enough to clear the
        # weak-match threshold regardless of category.
        return None

    time_ = time_proximity_score(report_timestamp, incident_last_timestamp)
    text = text_similarity(report.description, incident_description)

    if loc is None:
        # Location missing on one side — can't use it as signal or as a
        # gate. Category match alone is too weak to trust here (see module
        # docstring above), so require near-duplicate-level text similarity
        # before allowing any match at all.
        if text < MIN_TEXT_SCORE_WHEN_LOCATION_UNKNOWN:
            return None
        score = (0.55 * text) + (0.3 * cat) + (0.15 * time_)
        return score * 0.85

    # Location and category carry the most correlation signal; text and
    # timing corroborate but rarely disambiguate on their own.
    return (0.4 * loc) + (0.3 * cat) + (0.2 * text) + (0.1 * time_)
