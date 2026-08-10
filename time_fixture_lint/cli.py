"""time_fixture_lint の CLI（``python3 -m time_fixture_lint ...``）。

サブコマンド:
  * ``check``  wall clock と比較されうる時刻依存 test data（絶対日付・固定 epoch）を検査し、
    clock 未保護のヒットがあれば非0で終了する（CI 向け）。既知の inert 誤検出は
    ``time_fixture_lint/allowlist.py`` に理由付きで登録されており毎回ノイズ扱いしない。

終了コード: 0 正常（violation 0件） / 1 violation あり / 2 用法エラー（argparse 既定）。

read-only レポーティングツール（本ツール自身は tests/ 配下のいずれにも書き込まない）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .scanner import Report, scan

EXIT_OK = 0
EXIT_VIOLATION = 1

_REPO_ROOT = Path(__file__).resolve().parent.parent


def render_text(report: Report) -> str:
    lines: list[str] = []
    by_status: dict[str, list] = {}
    for finding in report.findings:
        by_status.setdefault(finding.status, []).append(finding)

    order = ("violation", "no_consumer", "allowlisted", "protected")
    labels = {
        "violation": "VIOLATION（clock 未保護）",
        "no_consumer": "NO_CONSUMER（参照テスト不明・要確認）",
        "allowlisted": "ALLOWLISTED（inert と登録済み）",
        "protected": "protected（clock 保護マーカーあり）",
    }
    for status in order:
        items = by_status.get(status, [])
        if not items:
            continue
        lines.append(f"## {labels[status]} ({len(items)})")
        for f in sorted(items, key=lambda x: (x.path, x.line)):
            lines.append(f"  {f.path}:{f.line}  {f.name}={f.value!r}")
            lines.append(f"    {f.detail}")
        lines.append("")

    total = len(report.findings)
    violation_count = len(report.violations)
    lines.append(f"total hits={total} violations={violation_count}")
    return "\n".join(lines) + "\n"


def cmd_check(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    report = scan(root)
    print(render_text(report), end="")
    return EXIT_VIOLATION if report.violations else EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="time_fixture_lint",
        description="時刻依存 test data（絶対日付・固定 epoch）を検査し、wall clock 未保護のヒットを検出する",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check", help="tests/ 配下の時刻依存 test data を検査")
    p.add_argument("--root", default=str(_REPO_ROOT), help=f"repo root（既定 {_REPO_ROOT}）")
    p.set_defaults(func=cmd_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
