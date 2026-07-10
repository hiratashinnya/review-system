"""asset_parity の CLI（``python3 -m asset_parity ...``）。

サブコマンド:
  * ``check``  4資産ツリー（`.claude/` 正本 ／ `.github/` Copilot ／ `.codex/agents/`
    Codex CLI agent ／ `.agents/skills/` Codex CLI skill）の presence/absence マトリクスを
    出力し、非対応 gap があれば非0で終了する（CI 向け）。既知の意図的非移植
    （`.claude/tailoring-registry.md` 記載）は ``exempt`` として除外し、毎回ノイズ扱いしない。

終了コード: 0 正常（MISSING 0件・``--fail-on-stale`` 未指定または staleness flag も0件） /
1 MISSING あり、または ``--fail-on-stale`` 指定時に staleness flag あり / 2 用法エラー
（argparse 既定）。

read-only レポーティングツール（本ツール自身は 4 ツリーのいずれにも書き込まない）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import staleness as staleness_mod
from .report import build_report, render_json, render_text

EXIT_OK = 0
EXIT_DRIFT = 1

_REPO_ROOT = Path(__file__).resolve().parent.parent


def cmd_check(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    report = build_report(
        root,
        day_threshold=args.day_threshold,
        size_ratio_threshold=args.size_ratio_threshold,
    )

    if args.format in ("text", "both"):
        print(render_text(report), end="")
    if args.format in ("json", "both"):
        if args.format == "both":
            print()
        print(render_json(report))

    drift = report.missing_count > 0
    if args.fail_on_stale and report.stale_flag_count > 0:
        drift = True
    return EXIT_DRIFT if drift else EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="asset_parity",
        description="Claude Code / Copilot / Codex CLI 資産ツリーの presence/absence 検出",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check", help="4ツリーの presence/absence マトリクスを表示")
    p.add_argument("--root", default=str(_REPO_ROOT),
                   help=f"repo root（既定 {_REPO_ROOT}）")
    p.add_argument("--format", choices=("text", "json", "both"), default="text",
                   help="出力形式（既定 text）")
    p.add_argument("--day-threshold", type=int, default=staleness_mod.DEFAULT_DAY_THRESHOLD,
                   help=f"staleness flag の last-commit gap 閾値・日数（既定 "
                        f"{staleness_mod.DEFAULT_DAY_THRESHOLD}）")
    p.add_argument("--size-ratio-threshold", type=float,
                   default=staleness_mod.DEFAULT_SIZE_RATIO_THRESHOLD,
                   help=f"staleness flag の行数比閾値（既定 "
                        f"{staleness_mod.DEFAULT_SIZE_RATIO_THRESHOLD}）")
    p.add_argument("--fail-on-stale", action="store_true",
                   help="staleness flag があっても非0終了にする（既定は MISSING のみで判定）")
    p.set_defaults(func=cmd_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
