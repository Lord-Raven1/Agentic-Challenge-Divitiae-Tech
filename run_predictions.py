"""Generate predictions.jsonl from a campus reports CSV.

Usage:
    python run_predictions.py [--reports PATH] [--services PATH] [--output PATH] [--log PATH]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "source", "member2"))

import pipeline  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reports", default=pipeline.DEFAULT_REPORTS, help="input reports CSV")
    ap.add_argument("--services", default=pipeline.DEFAULT_SERVICES, help="campus_services.csv")
    ap.add_argument("--output", default="predictions.jsonl", help="predictions JSONL output")
    ap.add_argument("--log", default=None, help="optional decision log JSONL (with reasons) for the dashboard")
    args = ap.parse_args()

    predictions = pipeline.run(args.reports, args.services, args.output, args.log)
    print(f"wrote {len(predictions)} predictions to {args.output}")


if __name__ == "__main__":
    main()
