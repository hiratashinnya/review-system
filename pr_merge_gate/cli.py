"""Command-line entry point for owner-facing PR blocker reports."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Callable, Sequence, TextIO

from blocker_gate.auth import resolve_github_token
from blocker_gate.github import GitHubCollector

from .audit import build_owner_report
from .gate import PrMergeGateError, evaluate_owner_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pr-merge-gate")
    report = parser.add_subparsers(dest="command", required=True).add_parser(
        "report", help="owner向けにPR blockerをfresh再評価する"
    )
    report.add_argument("number", type=int, help="pull request number")
    report.add_argument("--repository", required=True, metavar="OWNER/REPO")
    report.add_argument(
        "--merge-method", choices=("merge", "rebase", "squash"), default="merge"
    )
    return parser


def _error_report(repository: str, number: int, method: str, reason: str) -> dict[str, Any]:
    return build_owner_report(
        repository, number, method, {"result": "ERROR", "primary_reason": reason}
    )


def run(
    argv: Sequence[str], *, stdout: TextIO, stderr: TextIO,
    collector_factory: Callable[[str | None], Any] = GitHubCollector,
    token_resolver: Callable[[], str | None] = resolve_github_token,
) -> int:
    args = build_parser().parse_args(list(argv))
    try:
        report = evaluate_owner_report(
            args.repository, args.number, args.merge_method,
            collector_factory=collector_factory, token=token_resolver(),
        )
    except (PrMergeGateError, OSError, ValueError):
        report = _error_report(
            args.repository, args.number, args.merge_method, "REPORT_UNAVAILABLE"
        )
    json.dump(report, stdout, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    stdout.write("\n")
    stderr.write(
        f"PR blocker report {report['verdict']} {report['reason']} "
        f"{args.repository}#{args.number}; owner action required\n"
    )
    return int(report["blocker_evidence"].get("exit_code", 20))


def main(argv: Sequence[str] | None = None) -> int:
    return run(sys.argv[1:] if argv is None else argv, stdout=sys.stdout, stderr=sys.stderr)
