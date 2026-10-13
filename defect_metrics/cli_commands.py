"""Run defect metrics commands and translate failures to exit codes."""

from __future__ import annotations
import json
import sys
from .cli_baseline import verify_baseline
from .cli_parser import build_parser
from .cli_report import _emit, build_report
from .cli_window import gather, resolve_now, resolve_window
from .collect import CollectionError
from .metrics import normalise_repository
from .model import IssueRecord, PullRequestRecord

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_ANOMALY = 20
EXIT_BASELINE_MISMATCH = 21


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


def _cmd_verify_baseline(args: argparse.Namespace, stdout, stderr) -> int:
    issues, pulls = gather(args.repository, args.issues_json, args.pulls_json, args.limit)
    payload, mismatches = verify_baseline(issues, pulls, args.repository)
    stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    if mismatches:
        for line in mismatches:
            stderr.write(f"BASELINE_MISMATCH: {line}\n")
        return EXIT_BASELINE_MISMATCH
    return EXIT_OK


def main(argv: list[str] | None = None, stdout=None, stderr=None) -> int:
    stdout = stdout if stdout is not None else sys.stdout
    stderr = stderr if stderr is not None else sys.stderr
    args = build_parser().parse_args(argv)
    try:
        normalise_repository(args.repository)
        if args.command == "report":
            return _cmd_report(args, stdout, stderr)
        if args.command == "verify-baseline":
            return _cmd_verify_baseline(args, stdout, stderr)
    except (CollectionError, ValueError) as exc:
        stderr.write(f"defect_metrics: {exc}\n")
        return EXIT_ERROR
    stderr.write(f"defect_metrics: 未知のサブコマンド {args.command!r}\n")
    return EXIT_ERROR
