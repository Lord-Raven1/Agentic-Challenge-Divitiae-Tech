"""Stress test for the conflict_candidate heuristic's real weakness: it's a
literal phrase list (CONFLICT_PHRASES in matching.py), so it only catches
contradiction/hedging language that happens to use one of those phrases.
This generates varied real-world paraphrases of "this contradicts/doubts
prior evidence" via the local LLM and measures how many our heuristic
actually catches vs misses.
"""
import json
import urllib.request

from matching import suggests_conflict

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:3b"

PROMPT = """Generate 25 short sentences (one per line, no numbering, no
explanation, no markdown) that a campus incident reporter might write when
their report CONTRADICTS or CASTS DOUBT ON a previous report about the same
incident. Examples of the *idea* (do not reuse this exact wording):
- someone claims the danger was a false alarm
- a witness disputes what an earlier reporter said
- new evidence undermines the initial assessment
- a report says the situation is actually less/more serious than believed
- someone says the previous report was inaccurate or exaggerated

Use NATURAL, VARIED phrasing — do not all start the same way, do not all
use the same sentence structure, avoid repeating exact phrases across lines.
Write them the way a real person filing a quick incident update would.

Output ONLY the 25 sentences, one per line, nothing else.
"""


def generate_conflict_sentences() -> list[str]:
    payload = {
        "model": MODEL,
        "prompt": PROMPT,
        "stream": False,
        "options": {"temperature": 0.9},
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    raw = result["response"]
    lines = [l.strip() for l in raw.strip().splitlines() if l.strip()]
    lines = [l for l in lines if not l.startswith("```")]
    return lines


if __name__ == "__main__":
    sentences = generate_conflict_sentences()
    print(f"generated {len(sentences)} conflict/contradiction sentences\n")

    caught, missed = [], []
    for s in sentences:
        if suggests_conflict(s):
            caught.append(s)
        else:
            missed.append(s)

    print(f"=== CAUGHT ({len(caught)}/{len(sentences)}) ===")
    for s in caught:
        print(f"  [x] {s}")

    print(f"\n=== MISSED ({len(missed)}/{len(sentences)}) ===")
    for s in missed:
        print(f"  [ ] {s}")

    recall = len(caught) / len(sentences) if sentences else 0.0
    print(f"\nrecall on this generated batch: {recall:.0%}")
