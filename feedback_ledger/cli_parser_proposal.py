"""Parser registration for proposal lifecycle commands."""

from .cli_proposal_decision import cmd_approve, cmd_apply_done, cmd_reject
from .cli_support import _parse_date


def register_proposal_decisions(sub):
    approve = sub.add_parser("approve", help="改訂案を承認する")
    approve.add_argument("--proposal", required=True)
    approve.add_argument("--triage", required=True, help="承認した棚卸し記録 id")
    approve.add_argument("--by", required=True, help="承認者")
    approve.add_argument("--reason", default="")
    approve.add_argument("--now", type=_parse_date, default=None)
    approve.set_defaults(func=cmd_approve)

    reject = sub.add_parser("reject", help="改訂案を却下する")
    reject.add_argument("--proposal", required=True)
    reject.add_argument("--by", required=True, help="判断者")
    reject.add_argument("--reason", required=True, help="却下理由")
    reject.add_argument("--triage", default="")
    reject.add_argument("--now", type=_parse_date, default=None)
    reject.set_defaults(func=cmd_reject)

    applied = sub.add_parser("apply-done", help="承認済みの改訂案を反映済みにする")
    applied.add_argument("--proposal", required=True)
    applied.add_argument("--issue-ref", required=True, dest="issue_ref")
    applied.add_argument("--applied-pr", required=True, type=int, dest="applied_pr")
    applied.set_defaults(func=cmd_apply_done)
