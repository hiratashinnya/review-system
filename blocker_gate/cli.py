"""blocker gate resolver CLI。stdout は control JSON 一件、要約は stderr。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, Sequence, TextIO

from .auth import resolve_github_token
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

    # Issue #345［A］: Actions が孤立ブランチへ置く repository 全体 snapshot の生成。
    snapshot = subparsers.add_parser(
        "snapshot", help="repository全体のblocker snapshotをstdoutへ生成"
    )
    snapshot.add_argument("--repository", required=True, metavar="OWNER/REPO")
    return parser

def run(
    argv: Sequence[str],
    *,
    stdout: TextIO,
    stderr: TextIO,
    collector_factory: Callable[[str | None], Any] = GitHubCollector,
) -> int:
    args = build_parser().parse_args(list(argv))
    if args.command == "snapshot":
        # 生成側は verdict を出さない（判定は読取側の gate が行う）。
        # pages_complete=false / errors 非空でも **stdout へは publish する**:
        # 読取側はそれらを見て fail-close でき、遮断された環境へ診断材料が渡る。
        collector = collector_factory(resolve_github_token())
        raw = collector.collect_repository(args.repository)
        json.dump(raw, stdout, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        stdout.write("\n")
        # Issue #345 F-345-04: GraphQL rate limit の実消費（telemetry のみ）。
        usage = getattr(collector, "last_rate_limit", None)
        rate_limit = "-"
        if isinstance(usage, dict):
            rate_limit = (
                f"cost={usage.get('cost')},"
                f"remaining={usage.get('remaining')},"
                f"reset_at={usage.get('reset_at')}"
            )
        errors = raw.get("errors") or []
        # Issue #345 F-345-03: 生成が全面失敗しても exit 0 を返していたため、
        # 恒久故障（例: GITHUB_TOKEN が GraphQL の blockedBy/subIssues/parent を
        # 読めない）が workflow 緑のまま隠れた。判定は fail-close 側に倒れるので
        # 誤 ALLOW は起きないが、機能が死んでいることに誰も気づけない。
        # **部分 snapshot の publish は維持したまま**、劣化を exit code で外へ出す
        # （呼出側＝workflow が publish 後に job を失敗させる）。
        degraded = bool(errors) or raw.get("pages_complete") is not True
        stderr.write(
            "blocker-gate snapshot "
            f"{args.repository} issues={len(raw.get('issues') or {})} "
            f"pages_complete={raw.get('pages_complete')} "
            f"errors={','.join(errors) or '-'} "
            f"rate_limit={rate_limit}\n"
        )
        if degraded:
            stderr.write(
                "blocker-gate snapshot DEGRADED: snapshot は publish したが"
                " 完全ではない。到達不能環境の gate はこの snapshot で"
                " fail-close する。\n"
            )
        return 20 if degraded else 0
    if args.command == "evaluate":
        try:
            raw: Mapping[str, Any] = json.loads(args.snapshot.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("snapshot must be object")
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            raw = {}
        result = evaluate_snapshot(raw)
    else:
        collector = collector_factory(resolve_github_token())
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
