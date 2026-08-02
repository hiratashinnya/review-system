"""blocker gate resolver CLI。stdout は control JSON 一件、要約は stderr。"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, Sequence, TextIO

from .github import GitHubCollector
from .resolver import evaluate_snapshot, resolve_issue, resolve_pull_request


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="blocker-gate")
    subparsers = parser.add_subparsers(dest="command", required=True)

    issue = subparsers.add_parser("issue", help="Issue-start graphをread-only評価")
    issue.add_argument("--repository", required=True, metavar="OWNER/REPO")
    issue.add_argument("--number", required=True, type=int)

    pr = subparsers.add_parser("pr", help="PR closing graphをread-only評価")
    pr.add_argument("--repository", required=True, metavar="OWNER/REPO")
    pr.add_argument("--number", required=True, type=int)
    pr.add_argument("--merge-method", required=True, choices=("merge", "rebase", "squash"))

    evaluate = subparsers.add_parser("evaluate", help="取得済みsnapshotをoffline評価")
    evaluate.add_argument("--snapshot", required=True, type=Path)
    return parser


def _token() -> str | None:
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")


def run(
    argv: Sequence[str],
    *,
    stdout: TextIO,
    stderr: TextIO,
    collector_factory: Callable[[str | None], Any] = GitHubCollector,
) -> int:
    args = build_parser().parse_args(list(argv))
    if args.command == "evaluate":
        try:
            raw: Mapping[str, Any] = json.loads(args.snapshot.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("snapshot must be object")
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            raw = {}
        result = evaluate_snapshot(raw)
    else:
        collector = collector_factory(_token())
        if args.command == "issue":
            result = resolve_issue(collector, args.repository, args.number)
        else:
            result = resolve_pull_request(
                collector, args.repository, args.number, args.merge_method
            )
    json.dump(result, stdout, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    stdout.write("\n")
    subject = result.get("subject") or {}
    stderr.write(
        "blocker-gate "
        f"{result['result']} {result['primary_reason']} "
        f"{result.get('repository') or '-'}#{subject.get('number', '-')}\n"
    )
    return int(result["exit_code"])


def main(argv: Sequence[str] | None = None) -> int:
    return run(sys.argv[1:] if argv is None else argv, stdout=sys.stdout, stderr=sys.stderr)
