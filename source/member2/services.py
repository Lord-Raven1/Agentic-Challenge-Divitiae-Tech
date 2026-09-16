"""Service directory and report-to-service mapping (campus_services.csv).

Responsibilities:
- load the fictional service directory and answer "is this service
  available at this time?" from its availability column;
- normalise the reporter-supplied category (misspelt, mis-cased, missing
  or shifted into the wrong column) into one of the directory's service
  types, falling back to description keywords;
- decide which services a report needs and which action type engages each
  service at a given severity.
"""
import csv
import re
from dataclasses import dataclass
from datetime import datetime, time
from typing import Dict, List, Optional

from rapidfuzz import fuzz, process

from signals import fuzzy_contains

SEVERITY_ORDER = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def sev_rank(severity: Optional[str]) -> int:
    try:
        return SEVERITY_ORDER.index(severity)
    except ValueError:
        return -1


@dataclass
class Service:
    service_id: str
    name: str
    service_type: str
    availability: str
    scope: str

    def is_available(self, at: Optional[datetime]) -> bool:
        text = self.availability.lower()
        # "24/7", "24/7 on-call" and ".../on-call" are always reachable.
        if at is None or "24/7" in text or "on-call" in text:
            return True
        match = re.search(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", text)
        if not match:
            return True
        start = time(int(match.group(1)), int(match.group(2)))
        end = time(int(match.group(3)), int(match.group(4)))
        return start <= at.time() < end


class ServiceDirectory:
    # Who picks up when a service with office hours is closed.
    FALLBACKS = {
        "SVC-MEDICAL": "SVC-EMS",
        "SVC-FACILITIES": "SVC-MANAGEMENT",
        "SVC-CLEANING": "SVC-FACILITIES",
        "SVC-IT": "SVC-MANAGEMENT",
        "SVC-ACCESS": "SVC-SECURITY",
        "SVC-COMMS": "SVC-MANAGEMENT",
        "SVC-COUNSELLING": "SVC-MANAGEMENT",
    }

    def __init__(self, csv_path: str):
        self.services: Dict[str, Service] = {}
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                sid = (row.get("service_id") or "").strip()
                if not sid:
                    continue
                self.services[sid] = Service(
                    service_id=sid,
                    name=(row.get("service_name") or "").strip(),
                    service_type=(row.get("service_type") or "").strip().lower(),
                    availability=(row.get("availability") or "").strip(),
                    scope=(row.get("scope") or "").strip(),
                )

    @property
    def ids(self):
        return set(self.services)

    def resolve(self, service_id: str, at: Optional[datetime]) -> str:
        """Follow fallbacks until an available service is found."""
        seen = set()
        while service_id in self.services and service_id not in seen:
            if self.services[service_id].is_available(at):
                return service_id
            seen.add(service_id)
            service_id = self.FALLBACKS.get(service_id, "SVC-MANAGEMENT")
        return service_id if service_id in self.services else "SVC-MANAGEMENT"


# --- Category normalisation -------------------------------------------------

CANONICAL_CATEGORIES = ["fire", "medical", "security", "facilities", "electrical",
                        "it", "accessibility", "environmental"]

CATEGORY_ALIASES = {
    "smoke": "fire", "fire alarm": "fire", "alarm": "fire", "hazmat": "fire",
    "health": "medical", "injury": "medical", "first aid": "medical", "ems": "medical",
    "safety": "security", "theft": "security", "intruder": "security", "police": "security",
    "maintenance": "facilities", "building": "facilities", "plumbing": "facilities",
    "lift": "facilities", "elevator": "facilities", "repairs": "facilities",
    "power": "electrical", "electricity": "electrical", "lighting": "electrical",
    "ict": "it", "network": "it", "wifi": "it", "wi fi": "it", "internet": "it",
    "technology": "it", "computer": "it", "systems": "it",
    "access": "accessibility", "disability": "accessibility", "mobility": "accessibility",
    "cleaning": "environmental", "hygiene": "environmental", "spill": "environmental",
    "waste": "environmental", "environment": "environmental", "contamination": "environmental",
}

# Ordered: earlier entries win when a description matches several.
DESCRIPTION_KEYWORDS = [
    ("fire", ["fire", "smoke", "burning", "flames", "sparks", "sprinkler"]),
    ("medical", ["collapsed", "unconscious", "injured", "injury", "bleeding", "fainting",
                 "breathing", "medical", "ambulance", "paramedic", "headache", "dead"]),
    ("security", ["suspicious", "intruder", "theft", "stolen", "weapon", "lockdown",
                  "breach", "missing", "trespass", "unknown person"]),
    ("electrical", ["power", "wiring", "electrical", "outage", "lights", "socket", "cable"]),
    ("it", ["wi fi", "wifi", "network", "login", "server", "computer", "printer",
            "learning platform", "authentication", "monitor"]),
    ("accessibility", ["wheelchair", "ramp", "accessible", "accessibility"]),
    ("environmental", ["spill", "glass", "trash", "garbage", "bin", "waste", "gas leak",
                       "cleaning", "mopping", "insects"]),
    ("facilities", ["leak", "water", "pipe", "lift", "elevator", "handrail", "window",
                    "door", "ceiling", "flood", "stairs"]),
]


def normalise_category(raw_category: str, description_norm: str) -> Optional[str]:
    raw = " ".join((raw_category or "").lower().replace("-", " ").replace("_", " ").split())
    if raw in CANONICAL_CATEGORIES:
        return raw
    if raw in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[raw]
    if raw:
        choices = CANONICAL_CATEGORIES + list(CATEGORY_ALIASES)
        match = process.extractOne(raw, choices, scorer=fuzz.ratio, score_cutoff=80)
        if match:
            return CATEGORY_ALIASES.get(match[0], match[0])
    return infer_category(description_norm)


def infer_category(description_norm: str) -> Optional[str]:
    if not description_norm:
        return None
    padded = f" {description_norm}"
    for category, keywords in DESCRIPTION_KEYWORDS:
        # Word-prefix match so "bin" doesn't fire on "cabinet".
        if any(f" {k}" in padded for k in keywords):
            return category
    for category, keywords in DESCRIPTION_KEYWORDS:
        if any(fuzzy_contains(description_norm, k) for k in keywords if " " not in k):
            return category
    return None


# --- Service requirements ---------------------------------------------------

PRIMARY_SERVICE = {
    "fire": "SVC-FIRE",
    "medical": "SVC-MEDICAL",
    "security": "SVC-SECURITY",
    "facilities": "SVC-FACILITIES",
    "electrical": "SVC-ELECTRICAL",
    "it": "SVC-IT",
    "accessibility": "SVC-ACCESS",
    "environmental": "SVC-CLEANING",
}


def _any(text: str, words) -> bool:
    return any(w in text for w in words)


def required_services(category: Optional[str], text: str, severity: str,
                      location_norm: str) -> List[str]:
    """Services this evidence calls for, primary first. Ids are logical
    (before availability fallback)."""
    needed: List[str] = []

    def add(sid):
        if sid not in needed:
            needed.append(sid)

    primary = PRIMARY_SERVICE.get(category)
    if primary:
        add(primary)

    if category == "fire":
        if _any(text, ["electrical", "socket", "panel", "wiring", "distribution", "power supply"]):
            add("SVC-ELECTRICAL")
    elif category == "electrical":
        if _any(text, ["smoke", "sparks", "burning", "flames", "fire"]):
            add("SVC-FIRE")
    elif category == "medical":
        if sev_rank(severity) >= sev_rank("CRITICAL") or _any(
                text, ["external emergency medical", "ambulance", "paramedic", "found dead"]):
            add("SVC-EMS")
        if "found dead" in text:
            add("SVC-SECURITY")
    elif category == "facilities":
        if _any(text, ["power extension", "electrical", "wiring", "socket"]) and \
                _any(text, ["water", "leak", "wet", "flood"]):
            add("SVC-ELECTRICAL")
        if _any(text, ["trapped", "occupants inside", "stopped between floors"]):
            add("SVC-SECURITY")
    elif category == "accessibility":
        if _any(text, ["lift", "elevator", "ramp needs repair", "door sensor", "stopped between floors"]):
            add("SVC-FACILITIES")
        if _any(text, ["trapped", "occupants inside", "stopped between floors"]):
            add("SVC-SECURITY")
        if _any(text, ["vehicle", "blocking", "blocked"]):
            add("SVC-SECURITY")
    elif category == "environmental":
        if "gas leak" in text:
            add("SVC-FIRE")
        if "flood" in text:
            add("SVC-FACILITIES")
    elif category == "security":
        if _any(text, ["fire alarm", "smoke"]):
            add("SVC-FIRE")

    if sev_rank(severity) >= sev_rank("CRITICAL"):
        add("SVC-MANAGEMENT")
    if sev_rank(severity) >= sev_rank("HIGH") and (
            "campus wide" in location_norm or "campus wide" in text or "multiple buildings" in text
            or "evacuat" in text or "lockdown" in text):
        add("SVC-COMMS")

    if not needed:
        # Nothing recognisable: route to the duty manager for triage rather
        # than guessing an operational service.
        add("SVC-MANAGEMENT")
    return needed


def engagement_action(service_id: str, severity: str, text: str) -> str:
    """Action type that first engages a service for this evidence."""
    high = sev_rank(severity) >= sev_rank("HIGH")
    medium = sev_rank(severity) >= sev_rank("MEDIUM")
    if service_id in ("SVC-MANAGEMENT", "SVC-COMMS", "SVC-COUNSELLING"):
        return "NOTIFY"
    if service_id in ("SVC-FIRE", "SVC-EMS", "SVC-MEDICAL"):
        return "DISPATCH"
    if service_id == "SVC-SECURITY":
        threat = _any(text, ["weapon", "armed", "breach", "lockdown", "trapped", "stopped between floors",
                             "occupants inside", "restricted", "forced", "found dead", "missing"])
        # Unverified "suspicious person" reports get a verification, not a
        # confrontation: avoids accusing e.g. an authorised contractor.
        return "DISPATCH" if (high and threat) or sev_rank(severity) >= 3 else "REQUEST_VERIFICATION"
    if service_id == "SVC-ELECTRICAL":
        return "DISPATCH" if high else "REQUEST_INSPECTION"
    if service_id == "SVC-FACILITIES":
        return "DISPATCH" if high else ("REQUEST_INSPECTION" if medium else "CREATE_TICKET")
    if service_id in ("SVC-IT", "SVC-CLEANING", "SVC-ACCESS"):
        return "DISPATCH" if high or (medium and service_id != "SVC-IT") else "CREATE_TICKET"
    return "DISPATCH" if high else "CREATE_TICKET"
