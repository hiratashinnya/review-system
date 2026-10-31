"""進行中の取り込み記録。当該 worktree の Git 管理領域に1件だけ置く。

防ぐ失敗：gitgate が開始していない merge（手動 merge 等）を continue/abort が
取り違えて確定・破棄すること、および同じ checkout での二重開始。
"""

import json
import os

from .base_error import BaseIntegrationError, require
from .base_git import git_path

NAME = "gitgate-base-integration.json"
POLICY = "gitgate-base-integration/2.0"


def state_path(workspace):
    return git_path(workspace, NAME)


def load(workspace):
    path = state_path(workspace)
    if not path.exists():
        return None
    try:
        record = json.loads(path.read_text())
    except (OSError, ValueError):
        record = None
    require(isinstance(record, dict) and record.get("policy_version") == POLICY,
            "BASE_STATE_INVALID: " + str(path))
    return record


def create(workspace, record):
    try:
        with state_path(workspace).open("x") as handle:
            json.dump({"policy_version": POLICY, **record}, handle)
    except FileExistsError as exc:
        raise BaseIntegrationError("BASE_OPERATION_PENDING") from exc


def update(workspace, record):
    path = state_path(workspace)
    temporary = path.with_name(NAME + ".tmp")
    temporary.write_text(json.dumps({"policy_version": POLICY, **record}))
    os.replace(temporary, path)


def clear(workspace):
    state_path(workspace).unlink(missing_ok=True)
