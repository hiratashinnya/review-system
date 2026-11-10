"""申し送り verb の CLI 登録。"""
from .finding_handoff_block import AGENTS
from .verb_handoff_post import cmd_handoff_post
from .verb_handoff_preview import cmd_handoff_preview
from .verb_handoff_recheck import cmd_handoff_recheck


def register(subparsers, add_issue):
    for name, func in (("handoff-preview", cmd_handoff_preview), ("handoff-post", cmd_handoff_post)):
        parser = subparsers.add_parser(name, help="申し送りのプレビュー・検証")
        add_issue(parser)
        parser.add_argument("--finding", required=True)
        parser.add_argument("--to", required=True)
        parser.add_argument("--agent", required=True, choices=AGENTS)
        if name == "handoff-post":
            parser.add_argument("--confirm")
        parser.set_defaults(func=func)
    parser = subparsers.add_parser("handoff-recheck", help="申し送りを再検証")
    add_issue(parser)
    parser.add_argument("--finding", action="append")
    parser.set_defaults(func=cmd_handoff_recheck)
