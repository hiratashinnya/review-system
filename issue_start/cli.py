"""issue-start adapter CLI。stdout は evidence JSON、stderr は一行要約。"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence, TextIO

from .gate import IssueStartError, IssueStartRequest, evaluate_issue_start, fail_closed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 -m issue_start")
    parser.add_argument("--entrypoint", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--issue", required=True, type=int)
    parser.add_argument("--branch-name", required=True)
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--base-oid", required=True)
    parser.add_argument("--base-pr", type=int)
    return parser


def run(argv: Sequence[str], *, stdout: TextIO, stderr: TextIO, cwd: Path | None = None) -> int:
    args = build_parser().parse_args(list(argv))
    request = None
    try:
        # CLI と hook が同じ request validator を通るよう payload parser 相当の dataclass を作る。
        request = IssueStartRequest(
            args.entrypoint, args.repository, args.issue, args.branch_name,
            args.base_ref, args.base_oid, args.base_pr,
        )
        from .gate import _request
        request = _request(request.__dict__)
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        evidence = evaluate_issue_start(request, cwd=cwd, token=token)
    except IssueStartError as exc:
        evidence = fail_closed(request, exc)
    json.dump(evidence, stdout, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    stdout.write("\n")
    stderr.write(
        f"issue-start {evidence['result']} {evidence['reason']} "
        f"policy={evidence['policy_version']}\n"
    )
    return int(evidence["exit_code"])


def main(argv: Sequence[str] | None = None) -> int:
    return run(sys.argv[1:] if argv is None else argv, stdout=sys.stdout, stderr=sys.stderr)
