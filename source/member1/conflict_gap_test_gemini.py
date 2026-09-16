"""Re-run of conflict_gap_test.py's 24 generated contradiction sentences,
this time against the Gemini-backed classifier instead of the keyword
heuristic, to measure the actual recall improvement.
"""
import time

from conflict_llm import suggests_conflict_llm
from matching import suggests_conflict

# Same batch generated in conflict_gap_test.py, pinned here so this is a
# fair apples-to-apples comparison against the same 0% keyword-recall set.
SENTENCES = [
    "The immediate response to the alarm turned out to be unnecessary.",
    "Some students reported seeing no actual threat during the evacuation.",
    "The investigation revealed no obvious signs of a real emergency.",
    "The security team insists no threats were made or found.",
    "Witnesses now say panic spread faster than the initial alarm indicated.",
    "New footage suggests the panic was less widespread than thought.",
    "Experts reviewed the situation and concluded the risk was overestimated.",
    "Reports indicate that the panic response was proportionate but unnecessarily intense.",
    "We have evidence suggesting students were not panicked initially.",
    "An independent review suggests the initial warning was appropriate.",
    "Witnesses now claim the panic was mostly confined to a few buildings.",
    "Evidence points to the alarm system malfunctioning during the incident.",
    "Security protocols were tightened as a result of this incident's review.",
    "The investigation uncovered that students were prepared and calm.",
    "Witnesses now say the panic was not as severe as earlier reports indicated.",
    "Experts recommend de-escalating the response to future similar incidents.",
    "We now believe the panic response was less necessary and less dramatic.",
    "The review suggests the panic was a local issue, not a systemic problem.",
    "Witnesses say the panic response was more robust and less intense.",
    "A new analysis shows the panic was more contained than initially believed.",
    "Security protocols will be adjusted based on the new findings of this incident.",
    "Reports now show that the panic spread less than what was initially feared.",
    "Witnesses now say the panic response was well-coordinated and contained.",
    "The investigation found no signs of a genuine threat to warrant such a response.",
]

PRIOR = "A fire alarm triggered evacuation of the building after smoke was reported."

if __name__ == "__main__":
    caught, missed, errors = [], [], []
    t0 = time.time()
    for s in SENTENCES:
        verdict = suggests_conflict_llm(s, PRIOR)
        if verdict is True:
            caught.append(s)
        elif verdict is False:
            missed.append(s)
        else:
            errors.append(s)
    elapsed = time.time() - t0

    print(f"=== CAUGHT ({len(caught)}/{len(SENTENCES)}) ===")
    for s in caught:
        print(f"  [x] {s}")

    print(f"\n=== MISSED / classified NOT-conflict ({len(missed)}/{len(SENTENCES)}) ===")
    for s in missed:
        print(f"  [ ] {s}")

    if errors:
        print(f"\n=== API ERRORS / fell back to None ({len(errors)}/{len(SENTENCES)}) ===")
        for s in errors:
            print(f"  [!] {s}")

    recall = len(caught) / len(SENTENCES)
    print(f"\nrecall: {recall:.0%}")
    print(f"total time: {elapsed:.2f}s ({elapsed / len(SENTENCES):.2f}s/call avg)")

    print(f"\n=== For comparison: keyword heuristic recall on same batch ===")
    kw_caught = sum(1 for s in SENTENCES if suggests_conflict(s))
    print(f"keyword recall: {kw_caught}/{len(SENTENCES)} ({kw_caught/len(SENTENCES):.0%})")
