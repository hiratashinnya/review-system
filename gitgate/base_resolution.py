"""Reject unrelated edits and index tampering before staging conflict resolutions."""

import os
from pathlib import Path
from .base_error import require
from .base_git import foreign_operation, git
from .base_snapshot import conflict_paths, snapshot


def validate_pending(workspace, operation, binding):
    require(operation is not None, "BASE_OPERATION_MISSING")
    expected = operation["binding"]
    keys = {"entry_id", "role", "agent_id", "task_key", "workspace", "repository", "branch"}
    require(all(binding[key] == expected[key] for key in keys), "BASE_OPERATION_BINDING_MISMATCH")
    current = snapshot(workspace)
    require(current["head"] == operation["original_head"]
            and current["merge_head"] == operation["request"]["base"]
            and not foreign_operation(workspace), "BASE_PENDING_MERGE_STATE_INVALID")
    return current


def stage_resolution(workspace, operation, binding):
    current = validate_pending(workspace, operation, binding)
    original = operation.get("merge_snapshot")
    require(isinstance(original, dict), "BASE_START_NOT_CONFIRMED")
    conflicts = set(operation["conflicts"])
    require(conflicts.issuperset(conflict_paths(current["index"])), "BASE_FOREIGN_CONFLICT")
    nonconflict = lambda records: [record for record in records if record[3] not in conflicts]
    require(nonconflict(current["index"]) == nonconflict(original["index"]),
            "BASE_NONCONFLICT_INDEX_CHANGED")
    changed = git(workspace, "diff", "--name-only", "--no-renames", "-z").stdout
    require({os.fsdecode(raw) for raw in changed.split(b"\0") if raw}.issubset(conflicts),
            "BASE_UNRELATED_EDIT_STOP")
    require(not git(workspace, "ls-files", "--others", "--exclude-standard", "-z").stdout,
            "BASE_UNTRACKED_EDIT_STOP")
    if conflicts:
        for name in conflicts:
            path = Path(workspace) / name
            if path.is_file() and not path.is_symlink():
                require(not any(line.startswith((b"<<<<<<< ", b">>>>>>> ", b"||||||| "))
                                for line in path.read_bytes().splitlines()),
                        "BASE_CONFLICT_MARKERS_STOP")
        git(workspace, "add", "--", *sorted(conflicts))
    staged = snapshot(workspace)
    require(not conflict_paths(staged["index"]), "BASE_UNRESOLVED_INDEX")
    require(git(workspace, "diff", "--quiet", allow_failure=True).returncode == 0,
            "BASE_UNSTAGED_EDIT_STOP")
    return staged
