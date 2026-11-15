"""Argparse interface for validated, role-scoped advisory operations."""

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parser() -> argparse.ArgumentParser:
    main = argparse.ArgumentParser(prog="python3 -m advisory")
    main.add_argument("--root", type=Path, default=ROOT)
    sub = main.add_subparsers(dest="action", required=True)
    create = sub.add_parser("new")
    create.add_argument("--topic", required=True)
    create.add_argument("--created-on", required=True)
    create.add_argument("--source", action="append", required=True)
    for key in ("evidence", "recommendation", "triage-rationale", "policy-version"):
        create.add_argument("--" + key, required=True)
    create.add_argument("--distinct-reason", default="")
    create.add_argument("--related", action="append", default=[])
    create.add_argument("--at")
    amend = sub.add_parser("amend")
    for key in ("evidence", "recommendation", "triage-rationale",
                "policy-version", "distinct-reason"):
        amend.add_argument("--" + key)
    amend.add_argument("--source", action="append")
    amend.add_argument("--related", action="append")
    transition = sub.add_parser("transition")
    transition.add_argument("--to", required=True, choices=("open", "triaged", "closed"))
    promote = sub.add_parser("promote")
    promote.add_argument("--existing-issue", required=True)
    for command in (amend, transition, promote):
        command.add_argument("--id", required=True)
        command.add_argument("--expected-sha256", required=True)
        command.add_argument("--reason", required=True)
        command.add_argument("--at")
    for command in (create, amend, transition, promote):
        command.add_argument("--base-ref", required=True)
    show = sub.add_parser("show")
    show.add_argument("--id", required=True)
    listing = sub.add_parser("list")
    listing.add_argument("--today", required=True)
    listing.add_argument("--stale-days", type=int, default=30)
    checking = sub.add_parser("check")
    checking.add_argument("--against-ref")
    checking.add_argument("--require-base", action="store_true")
    return main
