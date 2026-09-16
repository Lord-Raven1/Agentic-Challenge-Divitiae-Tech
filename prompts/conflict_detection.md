# Conflict detection prompt (Member 1 — correlation layer)

Used by `source/member1/conflict_llm.py` to classify whether a new report
contradicts or casts doubt on the prior evidence for an incident it has
already been correlated to. This runs only for reports already classified
as UPDATE/CORROBORATION by the rules-based tracker (`tracker.py`) — never
for NEW or DUPLICATE reports, and never to decide correlation itself, only
to flag a conflict candidate for Member 2's decision engine.

Three-layer fallback chain, in order: **Gemini → local Qwen2.5-3B (Ollama)
→ keyword heuristic**. Each layer only runs if the one before it is
unavailable/fails — this call is an enhancement, not a dependency the
pipeline can crash on.

**Why this order — measured on a fair, matched-pair test batch (15 pairs,
identical data for all three):**

| Approach | Recall |
|---|---:|
| Gemini (`gemini-3.5-flash-lite`, temperature 0) | 13/15 (87%) |
| keyword heuristic | 4/15 (27%) |
| local Qwen2.5-3B (Ollama) | 1/15 (7%) |

Gemini is the clear winner on accuracy, so it's the primary backend.
Its free tier caps at 15 requests/minute (500/day is not a real
constraint), so `conflict_llm.py` self-paces calls and retries on HTTP 429
rather than giving up instantly. If Gemini is unreachable (no API key,
network failure, quota/billing issue), it falls back to local Qwen — no
rate limit since it runs on our own GPU, but far weaker accuracy. If
Ollama is also unreachable, it falls back to the keyword list, which is
free, instant, and needs no external service at all.

This ordering means the frozen judged run degrades gracefully rather than
failing outright if any one dependency (API key, network, local GPU) isn't
available at defence/replay time.

## System/user prompt template

```
You are checking whether a new incident report CONTRADICTS or CASTS DOUBT ON
the prior evidence for an ongoing campus incident. Answer only about whether
the new report undermines, disputes, or reduces confidence in what was
already reported — not just whether it adds new detail.

Prior incident evidence: "{prior_description}"
New report: "{new_description}"

Does the new report contradict, dispute, or cast doubt on the prior evidence?
Answer with exactly one word: YES or NO.
```

## Why this shape

- Single yes/no output keeps the call cheap and the response trivially
  parseable (no JSON parsing, no risk of a malformed structured response
  breaking the pipeline).
- Temperature 0 for determinism — the graded run is a single frozen replay,
  so we want the same input to always produce the same output.
- Only called for already-correlated reports (not all 300), keeping call
  volume and cost bounded.
