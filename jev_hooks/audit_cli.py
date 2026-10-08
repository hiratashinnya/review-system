"""Owner-facing metadata export, counters, and append-only review commands."""
import argparse
import json
import sqlite3
from .audit_export import counters, export, review


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", required=True)
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("export")
    actions.add_parser("counters")
    reviewer = actions.add_parser("review")
    reviewer.add_argument("record_id")
    reviewer.add_argument("rule", choices=["R1", "R2", "R3", "R4"])
    reviewer.add_argument("verdict", choices=["positive", "false_positive"])
    args = parser.parse_args()
    try:
        result = review(args.state_dir, args.record_id, args.rule, args.verdict) if args.action == "review" else export(args.state_dir)
        if args.action == "counters":
            result = counters(result)
    except (OSError, ValueError, sqlite3.Error):
        parser.exit(2, "jev-hooks: invalid review or unavailable audit storage\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
