"""backref の CLI（``python -m backref ...``）。

サブコマンド:
  * ``reverse <FND-id>...``  FND の辺逆転を実行。既定は ``--dry-run``（差分表示）、``--apply`` で書込。
  * ``check [--id GLOB]``     read-only 監査（辺逆転の不整合を列挙）。

終了コード: 0 正常 / 2 未検出 / 3 用法 / 4 config・前提違反（BackrefError/TraceScopeError）。
``check`` は error 級の指摘があれば 1 を返す（CI 連携用）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from docidx import scan

from . import check as check_mod
from . import reverse
from .errors import BackrefError

EXIT_OK = 0
EXIT_FINDINGS = 1  # check で error 級あり
EXIT_NOT_FOUND = 2
EXIT_USAGE = 3
EXIT_CONFIG = 4


def _index(args):
    root = Path(args.root).resolve() if args.root else scan.find_repo_root()
    config = Path(args.config).resolve() if args.config else None
    index, root = reverse.build_index(root, config)
    for nid, locs in index.duplicates.items():
        print(f"警告: ノード ID 重複 {nid}（{', '.join(locs)}）。先勝ち {locs[0]} を採用。",
              file=sys.stderr)
    return index, root


def cmd_reverse(args) -> int:
    index, root = _index(args)
    missing = [fid for fid in args.ids if fid not in index.by_id]
    if missing:
        print(f"未検出: {', '.join(missing)}", file=sys.stderr)
        return EXIT_NOT_FOUND
    any_changes = False
    for fid in args.ids:
        plan = reverse.plan_reverse(index, root, fid)
        for n in plan.notes:
            print(f"[{fid}] {n}")
        if plan.noop or not plan.new_text:
            continue
        any_changes = True
        print(f"\n=== {fid}: 辺逆転計画 ===")
        for a in plan.actions:
            tag = {"normal": "backref 付与", "provenance": "provenance（記録のみ）",
                   "missing": "付与先なし（記録のみ）"}[a.kind]
            if a.skipped_idempotent:
                tag = "backref 既存（冪等スキップ）"
            print(f"  →{a.to} [{a.kind}] {tag}")
        print(f"  DD-3: {plan.dd3_line}")
        if plan.notarget_line:
            print(f"  {plan.notarget_line}")
        print(f"  改訂理由（提示・本文へは未記入）: {plan.revision_note}")
        if args.apply:
            reverse.write_plan(plan, root)
            print(f"  適用済み: {', '.join(sorted(plan.new_text))}")
        else:
            print(plan.diff() or "  （差分なし）")
    if not args.apply and any_changes:
        print("\n（dry-run。書き込むには --apply を付けてください）")
    return EXIT_OK


def cmd_check(args) -> int:
    index, _ = _index(args)
    findings = check_mod.check(index)
    if args.id:
        import fnmatch
        findings = [f for f in findings if fnmatch.fnmatch(f.fnd_id, args.id)]
    if not findings:
        print("不整合は見つかりませんでした。")
        return EXIT_OK
    for f in sorted(findings, key=lambda x: (x.file, x.line, x.code)):
        print(f"{f.severity.upper():7} {f.fnd_id} [{f.code}] {f.message}  @ {f.file}:{f.line}")
    errors = sum(1 for f in findings if f.severity == "error")
    print(f"\n{len(findings)} 件（error {errors}）")
    return EXIT_FINDINGS if errors else EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", help="リポジトリ root（既定: doc-system/ を上方向に自動検出）")
    common.add_argument("--config", help="config.yaml のパス（既定: <root>/docs/doc-system/config.yaml）")

    parser = argparse.ArgumentParser(
        prog="backref",
        parents=[common],
        description="FND バックリファレンス（辺逆転）の決定的自動化・監査ツール",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_rev = sub.add_parser("reverse", parents=[common], help="FND の辺逆転を実行")
    p_rev.add_argument("ids", nargs="+", help="FND の ID（複数可）")
    p_rev.add_argument("--apply", action="store_true",
                       help="正本へ書き込む（既定は dry-run＝差分表示のみ）")
    p_rev.set_defaults(func=cmd_reverse)

    p_chk = sub.add_parser("check", parents=[common], help="辺逆転の不整合を監査（read-only）")
    p_chk.add_argument("--id", help="FND ID グロブで絞り込み（例: FND-1*）")
    p_chk.set_defaults(func=cmd_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except scan.TraceScopeError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return EXIT_CONFIG
    except BackrefError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return EXIT_CONFIG
    except BrokenPipeError:
        return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
