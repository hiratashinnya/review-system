"""Pure git argv builder; policy verbs remain unreachable here."""
from .cli_validation import GitgateError
from .cli_argv_basic import (
    verb_status, verb_add, verb_commit, verb_push, verb_branch_current,
    verb_new_branch, verb_fetch,
)
from .cli_argv_inspect import verb_diff, verb_log
VERB_HANDLERS = {
    "status": verb_status,
    "add": verb_add,
    "commit": verb_commit,
    "push": verb_push,
    "branch-current": verb_branch_current,
    "new-branch": verb_new_branch,
    "fetch": verb_fetch,
    "diff": verb_diff,
    "log": verb_log,
}


def build_git_argv(argv):
    """`argv`（verb + その引数の list）から固定テンプレートに沿った git argv を組み立てて返す。
    想定外の verb / 引数は GitgateError を送出する（副作用なし・純関数）。"""
    if not argv:
        raise GitgateError("missing verb; usage: python3 -m gitgate <verb> [args]")
    verb = argv[0]
    handler = VERB_HANDLERS.get(verb)
    if handler is None:
        allowed = ", ".join(sorted(VERB_HANDLERS))
        raise GitgateError(f"unknown verb {verb!r}; allowed verbs: {allowed}")
    return handler(argv[1:])
