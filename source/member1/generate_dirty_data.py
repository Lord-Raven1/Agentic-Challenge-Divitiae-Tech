"""Use a local Qwen2.5-3B (via Ollama) to generate a batch of messy/dirty
campus report rows for stress-testing the parser and tracker, matching the
schema in the Technical and Submission Guide (report_id, timestamp, location,
category, reported_severity, description, reporter_type).

Generates in batches (one LLM call per batch) since a single prompt stays
coherent for ~20 rows before quality/format drift sets in, then concatenates
and validates everything into one CSV sized to match the hidden test set.
"""
import csv
import io
import json
import sys
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:3b"
EXPECTED_FIELDS = 7
BATCH_SIZE = 20

PROMPT_TEMPLATE = """Generate {batch_size} rows of CSV test data for a campus incident-reporting system.

STRICT FORMAT RULE (this is the most important instruction): every row MUST
have EXACTLY 7 comma-separated fields, matching this column order:
report_id,timestamp,location,category,reported_severity,description,reporter_type

A "missing" value means the field is EMPTY (nothing between its two commas),
NOT that the field is dropped. Never shift columns. Never merge two columns
into one. Never add extra commas. If a description would naturally contain a
comma, wrap that field in double quotes.

Example rows showing the correct shape (7 fields every time, some blank):
R1001,2026-01-10T08:15,Library Level 2,facilities,MEDIUM,A pipe is leaking near the reference desk.,staff
R1002,,Library Level 2,facilities,MEDIUM,Leak appears worse than before.,student
R1003,2026-01-10 08:22,,fire,HIGH,Smoke reported near the electrical panel.,lecturer
R1004,garbled-not-a-date,Engineering Block E3,fire,,No further detail was given.,security
R1005,2026-01-10T08:30,Sports Centre,medical,critical,"Student collapsed, unresponsive, ambulance requested.",

Now generate {batch_size} NEW rows in exactly that shape, with this variety
spread across the batch:
- several rows with a blank timestamp
- several rows with a malformed timestamp (garbage text, wrong format/separators)
- several rows each with a blank location, category, reported_severity,
  description, or reporter_type (spread across different rows, not all in one)
- inconsistent casing on category/severity (e.g. "HIGH", "high", "High")
- extra whitespace padding around some values
- a couple of misspelled category or severity words
- a few rows that are near-duplicates of each other (same location/category,
  very similar description, arriving close in time) to test duplicate detection
- a few rows that are corroborating reports of the same incident from a
  different reporter_type, worded differently but describing the same event
- categories drawn from: facilities, fire, it, medical, accessibility, security, environmental, electrical, cleaning
- severities drawn from: LOW, MEDIUM, HIGH, CRITICAL (plus a couple of misspelled/miscased ones)
- report_id values {id_start}, {id_start_plus_1}, ... counting up (all unique, in order)
- descriptions short, plausible campus incident free text
- timestamps, where present, should fall on 2026-09-16 between 08:00 and 18:00

Output ONLY the {batch_size} CSV data rows. No header, no explanation, no
markdown fences, no code block, no commentary before or after. One row per
line. Before outputting, double check every row has exactly 6 commas
separating 7 fields.
"""


def build_prompt(id_start: int, batch_size: int) -> str:
    return PROMPT_TEMPLATE.format(
        batch_size=batch_size,
        id_start=f"R{id_start}",
        id_start_plus_1=f"R{id_start + 1}",
    )


def call_ollama(prompt: str, temperature: float = 0.7) -> str:
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["response"]


def clean_output(raw: str) -> str:
    lines = raw.strip().splitlines()
    lines = [l for l in lines if not l.strip().startswith("```")]
    lines = [l for l in lines if l.strip()]
    return "\n".join(lines)


def validate_rows(cleaned: str) -> tuple[list[str], list[str]]:
    """Drop any row the model still got wrong (wrong field count), rather
    than trusting free-form LLM output blindly. Uses csv.reader so a
    properly quoted comma inside a description doesn't count as a split."""
    good, bad = [], []
    for line in cleaned.splitlines():
        fields = next(csv.reader(io.StringIO(line)))
        if len(fields) == EXPECTED_FIELDS:
            good.append(line)
        else:
            bad.append(line)
    return good, bad


def generate_batch(id_start: int, batch_size: int = BATCH_SIZE) -> tuple[list[str], list[str]]:
    prompt = build_prompt(id_start, batch_size)
    raw = call_ollama(prompt)
    cleaned = clean_output(raw)
    return validate_rows(cleaned)


if __name__ == "__main__":
    total_target = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    out_path = "../../04_Development_Data/campus_reports_llm_massive.csv"

    all_good = []
    total_bad = 0
    id_counter = 3001
    batch_num = 0

    while len(all_good) < total_target:
        batch_num += 1
        remaining = total_target - len(all_good)
        size = min(BATCH_SIZE, remaining + 5)  # ask for a few extra to absorb rejects
        print(f"batch {batch_num}: requesting {size} rows starting at R{id_counter} "
              f"({len(all_good)}/{total_target} so far)...", flush=True)
        good, bad = generate_batch(id_counter, size)
        all_good.extend(good)
        total_bad += len(bad)
        id_counter += size + 10  # gap between batches so id ranges never collide
        print(f"  -> {len(good)} valid, {len(bad)} rejected", flush=True)

    all_good = all_good[:total_target]

    header = "report_id,timestamp,location,category,reported_severity,description,reporter_type"
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        f.write(header + "\n")
        f.write("\n".join(all_good) + "\n")

    print(f"\nwrote {out_path}: {len(all_good)} valid rows across {batch_num} batches "
          f"({total_bad} total rejected)")
