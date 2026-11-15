"""parser_inspect_args の責務。詳細は .ai/rationale/karte-module-split.md。"""
from .verb_check import cmd_check
from .verb_show import cmd_render, cmd_status

def register_render(subparsers, add_issue):
    render = subparsers.add_parser(
        "render", help="Prior attempts と未解消 finding を注入用の本文として出力"
    )
    add_issue(render)
    render.set_defaults(func=cmd_render)


def register_check(subparsers, add_issue):
    check = subparsers.add_parser("check", help="当該ラウンドの診断網羅を検査")
    add_issue(check)
    check.add_argument(
        "--round",
        help="検査対象のラウンド番号（省略時は tmp/_karte/active.json の round をそのまま使う）",
    )
    check.set_defaults(func=cmd_check)


def register_status(subparsers, add_issue):
    status = subparsers.add_parser("status", help="エスカレーション条件を機械判定")
    add_issue(status)
    status.add_argument("--json", action="store_true", help="機械可読な JSON で出力")
    status.set_defaults(func=cmd_status)
