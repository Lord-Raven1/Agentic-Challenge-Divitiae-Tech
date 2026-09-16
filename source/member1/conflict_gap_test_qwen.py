"""Fairer conflict-detection test than conflict_gap_test.py: generates
MATCHED (prior_description, contradicting_update) pairs so the classifier
has real context to judge against, instead of one mismatched generic prior
for all 24 sentences. Tests the local Qwen2.5-3B classifier (conflict_llm.py)
and the keyword heuristic (matching.suggests_conflict) on the same pairs.
"""
import json
import time
import urllib.request

from conflict_llm import suggests_conflict_llm
from matching import suggests_conflict

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:3b"

PROMPT = """Generate 15 pairs of campus-incident report lines. Each pair is:
1. An initial report describing an incident.
2. A follow-up report that CONTRADICTS or CASTS DOUBT ON the initial report
   (e.g. says it was a false alarm, disputes severity, says the danger
   wasn't real, undermines the original assessment).

Format each pair EXACTLY as two lines like this, with a blank line between
pairs, no numbering, no explanation:
INITIAL: <text>
FOLLOWUP: <text>

Use varied, natural phrasing across the 15 pairs — don't repeat the same
sentence structure or vocabulary. Keep each line under 20 words.
"""


def generate_pairs() -> list[tuple[str, str]]:
    payload = {"model": MODEL, "prompt": PROMPT, "stream": False, "options": {"temperature": 0.9}}
    req = urllib.request.Request(
        OLLAMA_URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    raw = result["response"]

    pairs = []
    current_initial = None
    for line in raw.strip().splitlines():
        line = line.strip()
        if line.upper().startswith("INITIAL:"):
            current_initial = line.split(":", 1)[1].strip()
        elif line.upper().startswith("FOLLOWUP:") and current_initial:
            followup = line.split(":", 1)[1].strip()
            pairs.append((current_initial, followup))
            current_initial = None
    return pairs


if __name__ == "__main__":
    pairs = generate_pairs()
    print(f"generated {len(pairs)} matched (initial, followup) pairs\n")

    llm_caught, llm_missed, llm_errors = [], [], []
    kw_caught_count = 0
    t0 = time.time()

    for initial, followup in pairs:
        verdict = suggests_conflict_llm(followup, initial)
        if verdict is True:
            llm_caught.append((initial, followup))
        elif verdict is False:
            llm_missed.append((initial, followup))
        else:
            llm_errors.append((initial, followup))

        if suggests_conflict(followup):
            kw_caught_count += 1

    elapsed = time.time() - t0

    print(f"=== Qwen LLM caught ({len(llm_caught)}/{len(pairs)}) ===")
    for i, f in llm_caught:
        print(f"  [x] INITIAL:  {i}")
        print(f"      FOLLOWUP: {f}")

    print(f"\n=== Qwen LLM missed ({len(llm_missed)}/{len(pairs)}) ===")
    for i, f in llm_missed:
        print(f"  [ ] INITIAL:  {i}")
        print(f"      FOLLOWUP: {f}")

    if llm_errors:
        print(f"\n=== Errors/fallback triggered ({len(llm_errors)}/{len(pairs)}) ===")
        for i, f in llm_errors:
            print(f"  [!] {f}")

    print(f"\nQwen recall: {len(llm_caught)}/{len(pairs)} ({len(llm_caught)/len(pairs):.0%})")
    print(f"keyword recall: {kw_caught_count}/{len(pairs)} ({kw_caught_count/len(pairs):.0%})")
    print(f"total time: {elapsed:.1f}s ({elapsed/len(pairs):.2f}s/call avg)")
