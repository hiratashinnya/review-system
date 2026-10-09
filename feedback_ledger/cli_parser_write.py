"""Parser registration for ledger and proposal draft commands."""

from .cli_entry import cmd_new_entry
from .cli_proposal_create import cmd_amend_proposal, cmd_propose


def register_write_commands(sub):
    new_entry = sub.add_parser("new-entry", help="台帳エントリを新規作成する")
    new_entry.add_argument("--from", dest="source", required=True, help="下書き TOML")
    new_entry.set_defaults(func=cmd_new_entry)

    propose = sub.add_parser("propose", help="改訂案を新規作成する")
    propose.add_argument("--from", dest="source", required=True, help="下書き TOML")
    propose.add_argument("--supersede", default="", help="置き換える既存の改訂案 id")
    propose.set_defaults(func=cmd_propose)

    amend = sub.add_parser("amend-proposal", help="pending の改訂案の本文を差し替える")
    amend.add_argument("--from", dest="source", required=True, help="下書き TOML")
    amend.set_defaults(func=cmd_amend_proposal)
