"""Public gitgate CLI facade: validated argv and exact policy verb dispatch."""
import subprocess
import sys
from datetime import datetime, timezone
from branch_source import BranchSourceError, create_branch, parse_new_branch_args
from .adopt import adopt_branch, parse_adopt_branch_args
from .worktree import (
    WorktreeError, collect_worktree, default_repo_root,
    parse_collect_worktree_args, parse_worktree_forget_args,
    parse_worktree_release_args, parse_worktree_sweep_args,
    sweep_abandoned_running, worktree_forget, worktree_release,
)
from .cli_validation import (
    GitgateError, BRANCH_NAME_RE, REF_RE, INTEGER_RE, _reject_control_chars,
    validate_path, validate_branch_name, validate_ref, validate_integer,
    validate_grep_pattern,
)
from .cli_argv_basic import (
    _require_no_args, verb_status, verb_add, verb_commit, verb_push,
    verb_branch_current, verb_new_branch, verb_fetch,
)
from .cli_argv_inspect import verb_diff, verb_log
from .cli_argv import VERB_HANDLERS, build_git_argv
from .cli_worktree import run_worktree_verb
WORKTREE_VERBS = (
    "worktree-release", "collect-worktree", "worktree-forget",
    "worktree-sweep-abandoned",
)
def _now():
    """wall clock を読むのは CLI 境界だけ（`.claude/rules/04-test-data.md`）。

    `gitgate/worktree.py` は `now` を引数で受け取るだけで `datetime.now()` を呼ばない。
    """
    return datetime.now(timezone.utc)
def _run_worktree_verb(verb, args):
    return run_worktree_verb(verb, args, now=_now)
def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    try:
        if argv and argv[0] == "adopt-branch":
            request = parse_adopt_branch_args(argv[1:])
            result = adopt_branch(request)
            sys.stderr.write(
                "gitgate: adopt-branch "
                f"{result.repository}@{result.expected_oid} "
                f"pr={result.pr if result.pr is not None else '-'} "
                f"policy={result.policy_version}\n"
            )
            sys.stderr.write(
                f"gitgate: adopted existing branch '{request.branch_name}' (checkout performed)\n"
            )
            return 0
        if argv and argv[0] in WORKTREE_VERBS:
            return _run_worktree_verb(argv[0], argv[1:])
        if argv and argv[0] == "new-branch":
            request = parse_new_branch_args(argv[1:])
            result = create_branch(request)
            sys.stderr.write(
                "gitgate: new-branch source "
                f"{result.source_kind} {result.repository}@{result.source_oid} "
                f"policy={result.policy_version}\n"
            )
            sys.stderr.write(
                f"gitgate: switched to new branch '{request.branch_name}' (checkout performed)\n"
            )
            return 0
        git_argv = build_git_argv(argv)
    except BranchSourceError as exc:
        sys.stderr.write(f"gitgate: {exc}\n")
        return 2
    except WorktreeError as exc:
        sys.stderr.write(f"gitgate: {exc}\n")
        return 2
    except GitgateError as exc:
        sys.stderr.write(f"gitgate: {exc}\n")
        return 2
    # shell=False で list 渡し（ユーザ制御文字列はシェルに解釈されない）。
    completed = subprocess.run(git_argv, shell=False)
    return completed.returncode
