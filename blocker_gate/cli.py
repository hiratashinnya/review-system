"""blocker gate resolver CLI。stdout は control JSON 一件、要約は stderr。"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, Sequence, TextIO

from .auth import resolve_github_token
from .github import GitHubCollector
from .model import POLICY_VERSION
from .resolver import evaluate_snapshot, resolve_issue, resolve_pull_request


# annotation 1行に詰め込む Issue ref の上限。超過分は件数だけ残す
# （Actions の annotation は1行表示であり、長すぎると読めなくなる）。
_MAX_REPORTED_REFS = 5


def format_unrecognized_state_reasons(raw: Any) -> str:
    """collector が観測した「本 policy 版が知らない state reason」を1行にする。

    Issue #466: 未知 reason は `CLOSED_OTHER` として closed 側へ倒すため判定は
    止まらない。止まらない以上、増えたこと自体を外へ出さないと誰も気づけないので、
    ここで検知結果を可視化する。**telemetry であり判定材料ではない**——欠落・型不正は
    例外にせず空文字を返す（`last_rate_limit` と同じ扱い）。
    """
    if not isinstance(raw, dict) or not raw:
        return ""
    parts: list[str] = []
    for reason, refs in sorted(raw.items()):
        if not isinstance(reason, str):
            continue
        listed = sorted(refs) if isinstance(refs, (set, frozenset, list, tuple)) else []
        head = ",".join(listed[:_MAX_REPORTED_REFS])
        suffix = f"(+{len(listed) - _MAX_REPORTED_REFS})" if len(listed) > _MAX_REPORTED_REFS else ""
        parts.append(f"{reason}={head}{suffix}" if head else reason)
    return "; ".join(parts)


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
        # Issue #466: policy 2.0 が知らない state reason の観測を外へ出す。
        # **exit code は変えない**——未知 reason は `CLOSED_OTHER` として closed 側へ
        # 倒すので判定は続行でき、ここで job を失敗させると「GitHub が enum を1つ
        # 増やしただけ」で gate の材料供給が止まる。逆に何も出さないと、判定が
        # 通ってしまう分だけ誰も語彙の増加に気づけない。だから止めずに知らせる。
        unrecognized = format_unrecognized_state_reasons(
            getattr(collector, "unrecognized_state_reasons", None)
        )
        if unrecognized:
            stderr.write(
                "blocker-gate snapshot UNRECOGNIZED_STATE_REASON "
                f"{unrecognized}\n"
            )
            if os.environ.get("GITHUB_ACTIONS") == "true":
                # Actions の annotation（run 一覧・summary に出る）。warning なので
                # job は緑のまま＝運用者には届くが自動化は止まらない。
                stderr.write(
                    "::warning title=blocker-gate: unrecognized issue state reason::"
                    f"policy {POLICY_VERSION} が知らない state reason を観測した: "
                    f"{unrecognized}. closed として評価を続行している"
                    " (blocker_gate.model.KNOWN_STATE_REASONS を更新すること)\n"
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
