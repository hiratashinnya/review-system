"""Atomic integration reservation and completion in the canonical dispatch ledger."""

import copy
import os
import secrets
from issue_start import worktree_ledger
from .base_error import require
from .base_git import process_alive, process_token

TERMINAL = {"committed", "aborted", "no_change", "rejected"}


def active_operation(entry):
    events = entry.get("base_integrations", [])
    require(isinstance(events, list), "BASE_LEDGER_INVALID")
    return events[-1] if events and events[-1].get("state") not in TERMINAL else None


def reserve(root, entry, binding, before, *, request=None, action="start"):
    token = secrets.token_hex(16)
    result = {}
    def mutate(document):
        matches = [item for item in document["entries"]
                   if item.get("entry_id") == entry["entry_id"]]
        require(len(matches) == 1 and matches[0] == entry, "BASE_LEDGER_CAS_MISMATCH")
        target = matches[0]
        pending = active_operation(target)
        if action == "start":
            require(pending is None, "BASE_OPERATION_PENDING")
            pending = {"schema_version": 1, "policy_version": "gitgate-base-integration/1.0",
                       "id": token, "binding": binding, "request": request,
                       "original_head": before["head"], "before": before,
                       "history": []}
            target.setdefault("base_integrations", []).append(pending)
        else:
            require(pending is not None, "BASE_OPERATION_MISSING")
            require(not process_alive(pending.get("owner_pid"), pending.get("owner_token")),
                    "BASE_OPERATION_ACTIVE")
        pending.update(owner_pid=os.getpid(), owner_token=process_token(),
                       reservation=token, state="reserved", action=action)
        pending["history"].append({"action": action, "snapshot": before,
                                   "reservation": token})
        result.update(copy.deepcopy(pending))
    worktree_ledger.update_ledger(root, mutate)
    return result


def finish(root, entry_id, operation, state, *, release=True, **evidence):
    def mutate(document):
        target = next(item for item in document["entries"] if item["entry_id"] == entry_id)
        pending = active_operation(target)
        require(pending is not None and pending["id"] == operation["id"]
                and pending.get("reservation") == operation["reservation"],
                "BASE_OPERATION_FENCED")
        pending.update(state=state, **evidence)
        if release:
            pending.update(owner_pid=None, owner_token=None)
        pending["history"].append({"state": state, **evidence})
    worktree_ledger.update_ledger(root, mutate)
