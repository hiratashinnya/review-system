"""Parser registration for weekly triage commands."""

from .cli_triage import cmd_triage_close, cmd_triage_open
from .cli_support import _parse_date


def register_triage_commands(sub):
    triage_open = sub.add_parser("triage-open", help="棚卸しの下書きを生成する")
    triage_open.add_argument("--week", required=True, help="YYYY-Wnn")
    triage_open.add_argument("--now", type=_parse_date, default=None)
    triage_open.set_defaults(func=cmd_triage_open)

    triage_close = sub.add_parser("triage-close", help="棚卸し記録を確定する")
    triage_close.add_argument("--from", dest="source", required=True, help="下書き TOML")
    triage_close.set_defaults(func=cmd_triage_close)
