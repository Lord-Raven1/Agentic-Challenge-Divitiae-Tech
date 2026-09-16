"""Fair re-test of Gemini on conflict detection, now that billing/credits
may have lifted the earlier 429 rate limit. Uses the SAME matched
(initial, followup) pairs as conflict_gap_test_qwen.py so all three
approaches (keyword heuristic, local Qwen, Gemini) are compared on
identical data.
"""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from matching import suggests_conflict

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
if _ENV_FILE.exists():
    for _line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _, _value = _line.partition("=")
            os.environ.setdefault(_key.strip(), _value.strip().strip('"').strip("'"))

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
API_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
)

PROMPT_TEMPLATE = """You are checking whether a new incident report CONTRADICTS or CASTS DOUBT ON
the prior evidence for an ongoing campus incident. Answer only about whether
the new report undermines, disputes, or reduces confidence in what was
already reported — not just whether it adds new detail.

Prior incident evidence: "{prior_description}"
New report: "{new_description}"

Does the new report contradict, dispute, or cast doubt on the prior evidence?
Answer with exactly one word: YES or NO."""

# Same 15 pairs conflict_gap_test_qwen.py generated and tested Qwen against.
PAIRS = [
    ("A fire alarm went off in the library, evacuation order issued.",
     "Emergency notification system glitch caused false alarm, no fire detected."),
    ("Security cameras detected suspicious activity near the campus gate.",
     "Surveillance footage shows the area was normal all day, no unusual presence."),
    ("The main entrance gate was locked, causing traffic jams.",
     "Gate unlocked shortly after report, traffic flow returned to normal."),
    ("Reports of a shooting were received at the sports stadium.",
     "Eyewitnesses say a nearby construction site accident was mistakenly reported."),
    ("Power outage was reported, affecting campus computers.",
     "System failure due to a software update, not a power issue."),
    ("There was an unauthorized person on campus grounds.",
     "Unauthorized access claim unsubstantiated, regular security checks showed no visitor."),
    ("The campus health center experienced an influx of flu patients.",
     "Seasonal flu peak, no indication of an outbreak or unusual situation."),
    ("Smoke was spotted coming from the roof of the tallest building.",
     "Mistakenly identified as smoke from a construction site, no fire reported."),
    ("Students reported feeling unsafe in the night-time.",
     "Night-time patrols increased, crime stats showed no unusual incidents."),
    ("Water leak alert was issued in the student housing.",
     "Plumbing issue resolved, no damage reported, no leak confirmed."),
    ("Reports of a chemical spill in the lab.",
     "No contamination detected, lab tests show all materials within limits."),
    ("There was a report of vandalism in the classrooms.",
     "Cleaning crews found no signs of damage, all classrooms secure."),
    ("An earthquake tremor was detected, alert sent to campus.",
     "Seismic activity within normal limits, no damage confirmed, no evacuation order."),
    ("There were reports of a missing student from the residence hall.",
     "All hall residents accounted for, no signs of a missing person."),
    ("Reports of a robbery at the campus bookstore.",
     "Robbery claims baseless, bookstore manager denies incident, no evidence found."),
]


def call_gemini(new_description: str, prior_description: str):
    api_key = os.environ["GEMINI_API_KEY"]
    prompt = PROMPT_TEMPLATE.format(
        prior_description=prior_description.replace('"', "'"),
        new_description=new_description.replace('"', "'"),
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 20},
    }
    url = API_URL_TEMPLATE.format(model=GEMINI_MODEL, key=api_key)
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        text = result["candidates"][0]["content"]["parts"][0]["text"].strip().upper()
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

    if text.startswith("YES"):
        return True, None
    if text.startswith("NO"):
        return False, None
    return None, f"unparseable: {text!r}"


if __name__ == "__main__":
    caught, missed, errors = [], [], []
    t0 = time.time()
    for initial, followup in PAIRS:
        verdict, err = call_gemini(followup, initial)
        if verdict is True:
            caught.append((initial, followup))
        elif verdict is False:
            missed.append((initial, followup))
        else:
            errors.append((initial, followup, err))
        time.sleep(5)  # free tier is 15 RPM for this model; stay under that
    elapsed = time.time() - t0

    print(f"=== Gemini caught ({len(caught)}/{len(PAIRS)}) ===")
    for i, f in caught:
        print(f"  [x] {f}")

    print(f"\n=== Gemini missed ({len(missed)}/{len(PAIRS)}) ===")
    for i, f in missed:
        print(f"  [ ] {f}")

    if errors:
        print(f"\n=== Errors ({len(errors)}/{len(PAIRS)}) ===")
        for i, f, err in errors:
            print(f"  [!] {f}  -- {err}")

    denom = len(caught) + len(missed)
    print(f"\nGemini recall (excluding errors): {len(caught)}/{denom} ({len(caught)/denom:.0%})" if denom else "no successful calls")
    print(f"total errors: {len(errors)}/{len(PAIRS)}")
    print(f"total time: {elapsed:.1f}s ({elapsed/len(PAIRS):.2f}s/call avg)")

    kw_caught = sum(1 for _, f in PAIRS if suggests_conflict(f))
    print(f"\nfor comparison -- keyword recall: {kw_caught}/{len(PAIRS)} ({kw_caught/len(PAIRS):.0%})")
    print("for comparison -- Qwen recall (from earlier run): 1/15 (7%)")
