"""``python3 -m maintainability_lint`` の read-only CLI。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .baseline import BaselineError
from .model import Report
from .scanner import build_baseline, scan


EXIT_OK = 0
EXIT_VIOLATION = 1
EXIT_CONFIGURATION = 2
REPO_ROOT = Path(__file__).resolve().parent.parent


def render_text(report: Report) -> str:
    violations = [item for item in report.findings if item.status == "violation"]
    accepted = [item for item in report.findings if item.status == "accepted-debt"]
    lines: list[str] = []
    for heading, items in (("VIOLATION", violations), ("ACCEPTED_DEBT", accepted)):
        if not items:
            continue
        lines.append(f"## {heading} ({len(items)})")
        for item in sorted(items, key=lambda value: (value.path, value.line, value.rule)):
            lines.append(f"  {item.path}:{item.line} [{item.rule}] {item.detail}")
        lines.append("")
    lines.append(f"violations={len(violations)} accepted_debt={len(accepted)}")
    return "\n".join(lines) + "\n"


def _check(args: argparse.Namespace) -> int:
    try:
        report = scan(Path(args.root).resolve())
    except (BaselineError, SyntaxError, UnicodeError) as exc:
        print(f"maintainability_lint: configuration/source error: {exc}", file=sys.stderr)
        return EXIT_CONFIGURATION
    print(render_text(report), end="")
    return EXIT_VIOLATION if any(item.status == "violation" for item in report.findings) else EXIT_OK


def _baseline(args: argparse.Namespace) -> int:
    baseline = build_baseline(Path(args.root).resolve())
    print(json.dumps(baseline, ensure_ascii=False, indent=2, sort_keys=True))
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="maintainability_lint")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, function, help_text in (
        ("check", _check, "check the repository against the committed debt baseline"),
        ("baseline", _baseline, "print the current debt snapshot as JSON"),
    ):
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("--root", default=str(REPO_ROOT))
        command.set_defaults(func=function)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
