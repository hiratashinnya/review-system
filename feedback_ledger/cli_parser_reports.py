"""Parser registration for validation and read-only report commands."""

from .cli_reports import cmd_check, cmd_index, cmd_render, cmd_status
from .cli_support import _parse_date


def register_report_commands(sub):
    check = sub.add_parser("check", help="機械 lint")
    check.add_argument("--canonical", action="store_true", help="L7（canonical バイト比較）も行う")
    check.add_argument("--base-ref", default=None, dest="base_ref",
                       help="immutability/状態遷移の比較対象（既定: origin/main → main）")
    check.add_argument(
        "--require-base", action="store_true", dest="require_base",
        help=(
            "比較対象（merge base）を解決できないことを ERROR にする。"
            "base を解決できる前提の実行環境（fetch-depth: 0 の CI）で指定し、"
            "L6/P1 が無言で skip されたまま緑になるのを防ぐ"
        ),
    )
    check.set_defaults(func=cmd_check)

    status = sub.add_parser("status", help="導出状態と滞留")
    status.add_argument("--now", type=_parse_date, default=None,
                        help="滞留判定の基準日（テスト・再現用の注入点）")
    status.add_argument("--json", action="store_true")
    status.add_argument("--entry", default="")
    status.set_defaults(func=cmd_status)

    index = sub.add_parser("index", help="文書の一覧")
    index.add_argument("--json", action="store_true")
    index.set_defaults(func=cmd_index)

    render = sub.add_parser("render", help="生存・訂正関係を Markdown に描画する")
    render.set_defaults(func=cmd_render)
