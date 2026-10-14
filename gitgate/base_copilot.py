"""Explicit local authorization for one exact PR base operation; not host authentication."""

import secrets
from pathlib import Path
from issue_start import worktree_ledger
from branch_source.policy import _remote_repository
from .base_error import require
from .base_git import output, foreign_operation
from .base_journal import active_operation
from .base_live import verify_live
from .base_snapshot import snapshot
from .base_records import authorization_records, operation_records

REGISTER = "integrate-base-copilot-register"


def workspace_binding(workspace):
    path = Path(workspace).resolve(strict=True)
    root = worktree_ledger.main_worktree_root(path).resolve(strict=True)
    require(Path(output(path, "rev-parse", "--show-toplevel")).resolve() == path,
            "BASE_WORKSPACE_INVALID")
    return root, {"workspace": str(path),
                  "repository": _remote_repository(output(path, "remote", "get-url", "origin")),
                  "branch": output(path, "symbolic-ref", "--quiet", "--short", "HEAD")}


def register(workspace, request, api):
    root, binding = workspace_binding(workspace)
    relative = Path(binding["workspace"]).relative_to(root).as_posix()
    before = snapshot(workspace)
    require(not before["status"] and not before["merge_head"]
            and not foreign_operation(workspace), "BASE_WORKTREE_NOT_CLEAN")
    require(before["head"] == request["head"], "BASE_HEAD_OID_MISMATCH")
    verify_live(workspace, request, binding, api)
    require(snapshot(workspace) == before, "BASE_CONTENT_CAS_MISMATCH")
    session = secrets.token_hex(16)
    entry = {"entry_id": "cb-" + session, "platform": "copilot-local",
             "agent_type": "base-operator", "agent_id": session, "status": "authorized",
             "task_key": f"base:{request['repository']}:{request['pr']}",
             "worktree_path": relative, "branch_name": binding["branch"],
             "base_authorization": {"request": request, **binding}}
    def mutate(document):
        for current in operation_records(document):
            if current.get("worktree_path") != relative:
                continue
            require(not active_operation(current), "BASE_OPERATION_PENDING")
            require(current.get("status") not in {"open", "running"}, "BASE_DISPATCH_EXISTS")
        for current in authorization_records(document):
            if current.get("worktree_path") == relative and current.get("status") == "authorized":
                current["status"] = "revoked"
        require(snapshot(workspace) == before, "BASE_CONTENT_CAS_MISMATCH")
        document.setdefault("base_authorizations", []).append(entry)
    worktree_ledger.update_ledger(root, mutate)
    return {"status": "registered", "session": entry["entry_id"], "authorization": request}


def identity(root, entry, binding):
    authorization = entry.get("base_authorization")
    require(entry.get("platform") == "copilot-local"
            and entry.get("agent_type") == "base-operator" and entry.get("agent_id")
            and entry.get("status") == "authorized" and isinstance(authorization, dict),
            "BASE_COPILOT_AUTHORIZATION_INVALID")
    require(all(authorization.get(key) == binding[key]
                for key in ("workspace", "repository", "branch")), "BASE_COPILOT_BINDING_MISMATCH")
    operation = active_operation(entry)
    require(not operation or operation["request"] == authorization.get("request"),
            "BASE_COPILOT_REQUEST_MISMATCH")
    binding.update(entry_id=entry["entry_id"], role="base-operator", agent_id=entry["agent_id"],
                   task_key=entry.get("task_key"), attempt=entry["agent_id"])
    return root, entry, binding
