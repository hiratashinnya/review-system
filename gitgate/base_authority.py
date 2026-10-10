"""Bind every operation to the trusted Claude dispatch ledger, never local state."""

from pathlib import Path
from issue_start import worktree_ledger
from branch_source.policy import _remote_repository
from .base_error import require
from .base_git import output


def identity(workspace):
    path = Path(workspace).resolve(strict=True)
    root = worktree_ledger.main_worktree_root(path).resolve(strict=True)
    require(path != root, "BASE_MAIN_WORKTREE_DENIED")
    require(Path(output(path, "rev-parse", "--show-toplevel")).resolve() == path,
            "BASE_WORKSPACE_INVALID")
    relative = path.relative_to(root).as_posix()
    entries = worktree_ledger.read_ledger(root)["entries"]
    matches = [entry for entry in entries if entry.get("worktree_path") == relative
               and entry.get("status") in {"open", "running"}]
    require(len(matches) == 1, "BASE_DISPATCH_MISSING")
    entry = matches[0]
    require(entry.get("agent_type") == "issue-fixer" and entry.get("agent_id"),
            "BASE_ROLE_DENIED")
    require(entry.get("platform", "claude") == "claude",
            "BASE_HOST_BOUNDARY_DENIED")
    require(entry.get("status") == "running", "BASE_DISPATCH_NOT_RUNNING")
    repository = _remote_repository(output(path, "remote", "get-url", "origin"))
    branch = output(path, "symbolic-ref", "--quiet", "--short", "HEAD")
    require(entry.get("branch_name") == branch, "BASE_BRANCH_MISMATCH")
    binding = {"entry_id": entry["entry_id"], "role": "issue-fixer",
               "agent_id": entry["agent_id"], "task_key": entry.get("task_key"),
               "workspace": str(path), "repository": repository, "branch": branch,
               "attempt": entry["agent_id"]}
    return root, entry, binding
