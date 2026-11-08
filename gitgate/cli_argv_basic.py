"""Fixed argv builders for basic and mutating git verbs."""
import os
from branch_source import BranchSourceError, parse_new_branch_args
from .cli_validation import GitgateError, _reject_control_chars, validate_path
def _require_no_args(verb, args):
    if args:
        raise GitgateError(f"`{verb}` takes no arguments; unexpected: {args!r}")


def verb_status(args):
    _require_no_args("status", args)
    return ["git", "status"]


def verb_add(args):
    # 全ての引数をパスとして扱い、`--` 以降に置く（オプション解釈を無効化）。最低1つ必要。
    if not args:
        raise GitgateError("`add` requires at least one path")
    paths = [validate_path(a) for a in args]
    return ["git", "add", "--", *paths]


def verb_commit(args):
    if len(args) != 1:
        raise GitgateError("`commit` requires exactly one argument: <message-file>")
    path = args[0]
    _reject_control_chars(path, "commit message file path")
    if not os.path.isfile(path):
        raise GitgateError(f"commit message file does not exist or is not a regular file: {path!r}")
    return ["git", "commit", "-F", path]


def verb_push(args):
    _require_no_args("push", args)
    return ["git", "push", "-u", "origin", "HEAD"]


def verb_branch_current(args):
    _require_no_args("branch-current", args)
    return ["git", "branch", "--show-current"]


def verb_new_branch(args):
    try:
        request = parse_new_branch_args(args)
    except BranchSourceError as exc:
        raise GitgateError(str(exc)) from exc
    # `main()` は branch_source policy を実行する。この builder の戻り値も
    # current HEAD を暗黙継承せず、検証済み exact OID を常に明示する。
    return ["git", "switch", "-c", request.branch_name, request.base_oid]


def verb_fetch(args):
    _require_no_args("fetch", args)
    return ["git", "fetch", "--prune", "origin"]
