"""``python3 -m defect_metrics`` の入口（Issue #488）。

サブコマンド
------------
``report``
    指定窓（既定＝``--now`` から遡る7日）の指標を算出し、機械可読な JSON を出力する。
    異常（:mod:`defect_metrics.threshold`）のときだけ stderr にアラート行を出し、
    exit code :data:`EXIT_ANOMALY` を返す。**異常でなければ stderr へ何も書かない。**
``verify-baseline``
    基線窓（``2026-08-02T00:00Z 〜 2026-08-16T00:00Z``）に対して同じ算出を行い、
    Issue #488「現状と根拠」の実測値（22 PR / 41 Issue / 1.86 / 派生 15 / 0.68）を
    再現できるかを機械的に照合する。ズレたら exit :data:`EXIT_BASELINE_MISMATCH`。

wall clock の読み取り
---------------------
現在時刻を読むのは :func:`resolve_now` **1箇所だけ**で、``--now`` が与えられたら
そちらを使う（`.claude/rules/04-test-data.md`「時刻依存 test data の規律」＝閾値判定の
「直近4週」が wall clock 依存になるため、テストからは常に固定値を注入できる形にする）。
指標算出（:mod:`defect_metrics.metrics`）と閾値判定（:mod:`defect_metrics.threshold`）は
現在時刻を一切読まず、渡された窓だけで決まる純粋な計算である。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone

from .collect import (
    DEFAULT_FETCH_LIMIT,
    CollectionError,
    fetch_issues,
    fetch_pulls,
    load_issues,
    load_pulls,
    read_json_file,
)
from .metrics import WindowMetrics, compute_window_metrics
from .model import (
    BASELINE_ALL_ISSUES,
    BASELINE_DERIVED_ISSUES,
    BASELINE_DERIVED_PER_PR,
    BASELINE_ISSUES_PER_PR,
    BASELINE_MERGED_PRS,
    BASELINE_WINDOW,
    DEFAULT_REPORT_WINDOW,
    RATIO_DIGITS,
    SCHEMA_VERSION,
    TRAILING_WINDOW,
    IssueRecord,
    PullRequestRecord,
    Window,
    format_timestamp,
    parse_timestamp,
)
from .threshold import Evaluation, evaluate

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_ANOMALY = 20
EXIT_BASELINE_MISMATCH = 21


def resolve_now(explicit: str | None) -> datetime:
    """現在時刻。``--now`` があればそれを使う（本パッケージ唯一の wall clock 読み取り）。"""
    if explicit:
        return parse_timestamp(explicit)
    return datetime.now(timezone.utc)


def resolve_window(
    now: datetime,
    start: str | None,
    end: str | None,
    days: float,
) -> Window:
    """``--window-start`` / ``--window-end`` / ``--window-days`` から窓を決める。

    両端が省略されたときだけ ``now`` を終端に採る（窓を明示すれば決定的になる）。
    """
    span = timedelta(days=days)
    if start and end:
        return Window(start=parse_timestamp(start), end=parse_timestamp(end))
    if start:
        begin = parse_timestamp(start)
        return Window(start=begin, end=begin + span)
    if end:
        finish = parse_timestamp(end)
        return Window(start=finish - span, end=finish)
    return Window(start=now - span, end=now)


def gather(
    repository: str,
    issues_json: str | None,
    pulls_json: str | None,
    limit: int,
) -> tuple[list[IssueRecord], list[PullRequestRecord]]:
    issues = (
        load_issues(read_json_file(issues_json)) if issues_json else fetch_issues(repository, limit)
    )
    pulls = (
        load_pulls(read_json_file(pulls_json)) if pulls_json else fetch_pulls(repository, limit)
    )
    return issues, pulls


def build_report(
    repository: str,
    window: Window,
    issues: list[IssueRecord],
    pulls: list[PullRequestRecord],
    now: datetime,
) -> tuple[dict[str, object], Evaluation]:
    """レポート JSON と閾値判定結果を作る。"""
    current = compute_window_metrics(window, issues, pulls)
    trailing_window = window.shifted_back(TRAILING_WINDOW)
    trailing = compute_window_metrics(trailing_window, issues, pulls)
    evaluation = evaluate(current, trailing)

    report: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "tool": "defect_metrics",
        "issue": 488,
        "repository": repository,
        "generated_at": format_timestamp(now),
        "report_window": current.as_dict(),
        "trailing_4_weeks": trailing.as_dict(),
        "baseline": {
            "source": "Issue #368「現状と根拠」（2026-09-06 訂正）／Issue #488「現状と根拠」",
            "window": BASELINE_WINDOW.as_dict(),
            "merged_prs": BASELINE_MERGED_PRS,
            "created_issues": BASELINE_ALL_ISSUES,
            "issues_per_pr": BASELINE_ISSUES_PER_PR,
            "derived_issues": BASELINE_DERIVED_ISSUES,
            "derived_per_pr": BASELINE_DERIVED_PER_PR,
        },
        "threshold": evaluation.as_dict(),
    }
    return report, evaluation


def _emit(report: dict[str, object], output: str | None, stdout) -> None:
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    if output:
        with open(output, "w", encoding="utf-8") as handle:
            handle.write(text)
    else:
        stdout.write(text)


def _cmd_report(args: argparse.Namespace, stdout, stderr) -> int:
    now = resolve_now(args.now)
    window = resolve_window(now, args.window_start, args.window_end, args.window_days)
    issues, pulls = gather(args.repository, args.issues_json, args.pulls_json, args.limit)
    report, evaluation = build_report(args.repository, window, issues, pulls, now)
    _emit(report, args.output, stdout)
    if not evaluation.anomaly:
        # 異常でなければ何も報告しない（Issue #488「異常でなければ何も報告しない」）。
        return EXIT_OK
    for line in evaluation.render_alert_lines():
        stderr.write(line + "\n")
    return EXIT_ANOMALY


def _mismatches(metrics: WindowMetrics) -> list[str]:
    expected = (
        ("merged_prs", BASELINE_MERGED_PRS, metrics.merged_prs),
        ("created_issues", BASELINE_ALL_ISSUES, metrics.created_issues),
        ("derived_issues", BASELINE_DERIVED_ISSUES, metrics.derived_issues),
        (
            "issues_per_pr",
            BASELINE_ISSUES_PER_PR,
            None if metrics.issues_per_pr is None else round(metrics.issues_per_pr, RATIO_DIGITS),
        ),
        (
            "derived_per_pr",
            BASELINE_DERIVED_PER_PR,
            None if metrics.derived_per_pr is None else round(metrics.derived_per_pr, RATIO_DIGITS),
        ),
    )
    return [
        f"{name}: expected {want}, got {got}" for name, want, got in expected if want != got
    ]


def _cmd_verify_baseline(args: argparse.Namespace, stdout, stderr) -> int:
    issues, pulls = gather(args.repository, args.issues_json, args.pulls_json, args.limit)
    metrics = compute_window_metrics(BASELINE_WINDOW, issues, pulls)
    stdout.write(
        json.dumps(
            {
                "baseline_window": BASELINE_WINDOW.as_dict(),
                "measured": metrics.as_dict(),
                "mismatches": _mismatches(metrics),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    mismatches = _mismatches(metrics)
    if mismatches:
        for line in mismatches:
            stderr.write(f"BASELINE_MISMATCH: {line}\n")
        return EXIT_BASELINE_MISMATCH
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m defect_metrics",
        description="欠陥混入率（派生 Issue/PR）の指標を算出する（Issue #488）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(target: argparse.ArgumentParser) -> None:
        target.add_argument("--repository", required=True, help="OWNER/REPO")
        target.add_argument("--issues-json", help="gh issue list --json 出力（省略時は gh を実行）")
        target.add_argument("--pulls-json", help="gh pr list --json 出力（省略時は gh を実行）")
        target.add_argument(
            "--limit", type=int, default=DEFAULT_FETCH_LIMIT, help="gh list の --limit"
        )

    report = sub.add_parser("report", help="レポート JSON を出力する")
    add_common(report)
    report.add_argument("--window-start", help="窓の開始（ISO8601・UTC・含む）")
    report.add_argument("--window-end", help="窓の終了（ISO8601・UTC・含まない）")
    report.add_argument(
        "--window-days",
        type=float,
        default=DEFAULT_REPORT_WINDOW.total_seconds() / 86400.0,
        help="窓の幅（日）。両端を省略したときは --now を終端に使う",
    )
    report.add_argument("--now", help="現在時刻を固定する（省略時のみ wall clock を読む）")
    report.add_argument("--output", help="出力先ファイル（省略時は stdout）")

    verify = sub.add_parser(
        "verify-baseline",
        help="基線窓の実測値（Issue #488「現状と根拠」）を再現できるか照合する",
    )
    add_common(verify)

    return parser


def main(argv: list[str] | None = None, stdout=None, stderr=None) -> int:
    stdout = stdout if stdout is not None else sys.stdout
    stderr = stderr if stderr is not None else sys.stderr
    args = build_parser().parse_args(argv)
    try:
        if args.command == "report":
            return _cmd_report(args, stdout, stderr)
        if args.command == "verify-baseline":
            return _cmd_verify_baseline(args, stdout, stderr)
    except (CollectionError, ValueError) as exc:
        stderr.write(f"defect_metrics: {exc}\n")
        return EXIT_ERROR
    stderr.write(f"defect_metrics: 未知のサブコマンド {args.command!r}\n")
    return EXIT_ERROR
