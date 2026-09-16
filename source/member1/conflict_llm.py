"""LLM-backed conflict detection, layered with fallbacks.

The keyword-based matching.suggests_conflict() has near-zero recall on
naturally-phrased contradiction language (measured empirically: 0/24 on a
first generated test batch). We tested three approaches on a fair,
matched-pair batch (15 pairs, same data for all three):

  - Gemini (gemini-3.5-flash-lite, temperature 0): 13/15 (87%) recall
  - keyword heuristic:           4/15  (27%) recall
  - local Qwen2.5-3B (Ollama):   1/15  (7%)  recall

Fallback order is Gemini -> keyword heuristic -> local Qwen, NOT accuracy
order. Gemini is primary since it's the clear accuracy winner. The keyword
heuristic is second, ahead of Qwen, because it needs no external service at
all — it always works, including in whatever environment actually runs the
submission, which may not have Ollama installed or a GPU available. Local
Qwen is a last-resort, effectively theoretical fallback: kept in the
codebase and documented, but not something the submission can depend on
being reachable.

The pipeline never crashes over any of this — it's an enhancement layer,
not a dependency. See prompts/conflict_detection.md for the full rationale.
"""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def _load_dotenv() -> None:
    """Minimal .env loader (no new dependency) — never overrides a variable
    already set in the real environment. The file itself is git-ignored."""
    if not _ENV_FILE.exists():
        return
    for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

# --- Gemini (primary) ---
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_API_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
)
GEMINI_TIMEOUT_SECONDS = 15
GEMINI_MAX_RETRIES = 3
GEMINI_FREE_TIER_MIN_INTERVAL = 1.5  # seconds; conservative floor — real limit is enforced by the 429 retry/backoff below, this just avoids hammering needlessly
_last_gemini_call_time = 0.0

# --- Local Qwen via Ollama (secondary fallback) ---
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_TIMEOUT_SECONDS = 20

PROMPT_TEMPLATE = """You are checking whether a new incident report CONTRADICTS or CASTS DOUBT ON
the prior evidence for an ongoing campus incident. Answer only about whether
the new report undermines, disputes, or reduces confidence in what was
already reported — not just whether it adds new detail.

Prior incident evidence: "{prior_description}"
New report: "{new_description}"

Does the new report contradict, dispute, or cast doubt on the prior evidence?
Answer with exactly one word: YES or NO."""


def _parse_yes_no(text: str) -> Optional[bool]:
    text = text.strip().upper()
    if text.startswith("YES"):
        return True
    if text.startswith("NO"):
        return False
    return None


def _call_gemini(prompt: str) -> Optional[bool]:
    global _last_gemini_call_time
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 20},
    }
    url = GEMINI_API_URL_TEMPLATE.format(model=GEMINI_MODEL, key=api_key)

    for attempt in range(GEMINI_MAX_RETRIES):
        # Self-pace to stay under the free-tier 15 RPM cap. Harmless (and
        # effectively a no-op) once/if billing removes the ceiling.
        elapsed = time.time() - _last_gemini_call_time
        if elapsed < GEMINI_FREE_TIER_MIN_INTERVAL:
            time.sleep(GEMINI_FREE_TIER_MIN_INTERVAL - elapsed)

        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=GEMINI_TIMEOUT_SECONDS) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            _last_gemini_call_time = time.time()
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            return _parse_yes_no(text)
        except urllib.error.HTTPError as e:
            _last_gemini_call_time = time.time()
            if e.code == 429:
                try:
                    body = e.read().decode("utf-8", errors="ignore").lower()
                except Exception:
                    body = ""
                # A depleted/exhausted billing balance is permanent for this
                # run — retrying wastes ~15s before falling back anyway.
                # Only a transient per-minute rate limit is worth retrying.
                permanent = "prepayment" in body or "depleted" in body
                if not permanent and attempt < GEMINI_MAX_RETRIES - 1:
                    time.sleep(GEMINI_FREE_TIER_MIN_INTERVAL * (attempt + 1))
                    continue
            return None
        except Exception:
            _last_gemini_call_time = time.time()
            return None
    return None


def _call_ollama(prompt: str) -> Optional[bool]:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0},
    }
    req = urllib.request.Request(
        OLLAMA_URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT_SECONDS) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        return _parse_yes_no(result["response"])
    except Exception:
        return None


def _llm_disabled() -> bool:
    """Read fresh each call (not cached at import) so a test suite can set
    this env var right before running and have it take effect immediately.
    Set CONFLICT_LLM_DISABLE=1 to skip both Gemini and Qwen calls entirely
    and fall straight through to the keyword heuristic — routine test runs
    (e.g. compliance_test.py across several hundred-report datasets) would
    otherwise make a live API call per correlated report, burning quota and
    taking minutes instead of seconds."""
    return os.environ.get("CONFLICT_LLM_DISABLE", "").strip().lower() in ("1", "true", "yes")


def suggests_conflict_gemini(new_description: str, prior_description: str) -> Optional[bool]:
    """Primary backend. Returns True/False, or None if unavailable/failed
    (no API key, network error, exhausted quota/billing) — callers must
    treat None as "try the next fallback", never as False."""
    if _llm_disabled() or not new_description or not prior_description:
        return None
    prompt = PROMPT_TEMPLATE.format(
        prior_description=prior_description.replace('"', "'"),
        new_description=new_description.replace('"', "'"),
    )
    return _call_gemini(prompt)


def suggests_conflict_qwen(new_description: str, prior_description: str) -> Optional[bool]:
    """Last-resort backend — only reachable in practice if you're running
    this locally with Ollama up; not something the submitted pipeline can
    assume is available. Kept for local dev/testing, not relied on."""
    if _llm_disabled() or not new_description or not prior_description:
        return None
    prompt = PROMPT_TEMPLATE.format(
        prior_description=prior_description.replace('"', "'"),
        new_description=new_description.replace('"', "'"),
    )
    return _call_ollama(prompt)


def suggests_conflict_llm(new_description: str, prior_description: str) -> Optional[bool]:
    """Backwards-compatible alias for the primary (Gemini) backend only.
    The full fallback chain (Gemini -> keyword -> Qwen) is orchestrated by
    the caller (tracker.py), not here, since the keyword heuristic lives in
    matching.py and needs to sit ahead of Qwen in that chain."""
    return suggests_conflict_gemini(new_description, prior_description)
