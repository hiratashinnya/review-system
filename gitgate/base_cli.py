"""PR base 取り込み verb の dispatcher と、進行中の通常 commit の拒否。

GitGate 本体はロール・ハーネスを同定しない。ロール別の許可は呼び出し元の
command gate が扱う（Issue #706）。
"""

import json
import sys
from pathlib import Path

from branch_source.policy import BranchSourceError
from .base_abort import abort
from .base_continue import continue_integration
from .base_error import BaseIntegrationError, require
from .base_git import git
from .base_live import default_api
from .base_request import parse_request
from .base_start import start
from .base_state import state_path
from .base_workspace import bind


def execute(verb, args, *, workspace=None, api=None):
    request = parse_request(verb, list(args))
    binding = bind(workspace or Path.cwd())
    if verb == "integrate-base":
        return start(binding, request, api or default_api())
    if verb == "integrate-base-abort":
        return abort(binding)
    return continue_integration(binding, api or default_api())


def refuse_pending_commit(workspace):
    """通常 commit が取り込み途中の merge を検証なしに確定するのを防ぐ。"""
    if git(workspace, "rev-parse", "--git-dir", allow_failure=True).returncode != 0:
        return
    require(not state_path(workspace).exists(), "BASE_PENDING_COMMIT_DENIED")


def run_cli(args):
    try:
        result = execute(args[0], args[1:])
        print(json.dumps(result, ensure_ascii=False))
        return 3 if result["status"] == "conflicts" else 0
    except (BaseIntegrationError, BranchSourceError) as exc:
        sys.stderr.write(f"gitgate: {exc}\n")
        return 2
