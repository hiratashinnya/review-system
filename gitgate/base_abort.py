"""Save all current edits before aborting only the ledger-bound merge."""

import io
import json
import os
import tarfile
from pathlib import Path
from .base_error import require
from .base_git import git, git_path
from .base_journal import finish, reserve
from .base_resolution import validate_pending
from .base_snapshot import snapshot


def save_recovery(root, workspace, operation, before):
    directory = Path(root) / "tmp" / "_base_integration_recovery"
    require(not directory.parent.is_symlink() and not directory.is_symlink(),
            "BASE_RECOVERY_SYMLINK")
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    target = directory / f"{operation['id']}-{operation['reservation']}.tar"
    require(not target.exists() and not target.is_symlink(), "BASE_RECOVERY_EXISTS")
    changed = git(workspace, "diff", "--name-only", "--no-renames", "-z", "HEAD").stdout
    others = git(workspace, "ls-files", "--others", "--exclude-standard", "-z").stdout
    names = sorted({os.fsdecode(raw) for raw in (changed + others).split(b"\0") if raw})
    with target.open("xb") as handle:
        os.fchmod(handle.fileno(), 0o600)
        write_archive(handle, workspace, operation, before, names)
        handle.flush()
        os.fsync(handle.fileno())
    require(snapshot(workspace) == before, "BASE_ABORT_CONTENT_CAS_MISMATCH")
    return str(target)


def write_archive(handle, workspace, operation, before, names):
    with tarfile.open(fileobj=handle, mode="w") as archive:
        for name in names:
            path = Path(workspace) / name
            require(not Path(name).is_absolute() and ".." not in Path(name).parts,
                    "BASE_RECOVERY_PATH_INVALID")
            if path.exists() or path.is_symlink():
                archive.add(path, arcname="worktree/" + name, recursive=False)
        for name in ("index", "MERGE_HEAD", "MERGE_MSG"):
            path = git_path(workspace, name)
            require(not path.is_symlink(), "BASE_RECOVERY_GIT_SYMLINK")
            if path.is_file():
                archive.add(path, arcname="git/" + name)
        raw = json.dumps({"operation": operation, "snapshot": before}).encode()
        info = tarfile.TarInfo("evidence.json")
        info.size = len(raw)
        archive.addfile(info, io.BytesIO(raw))


def abort(root, entry, binding, operation):
    workspace = binding["workspace"]
    before = validate_pending(workspace, operation, binding)
    reservation = reserve(root, entry, binding, before, action="abort")
    try:
        recovery = save_recovery(root, workspace, reservation, before)
        finish(root, entry["entry_id"], reservation, "aborting", release=False,
               recovery=recovery)
        git(workspace, "merge", "--abort")
        after = snapshot(workspace)
        require(after["head"] == operation["original_head"] and after["merge_head"] is None,
                "BASE_ABORT_RESULT_INVALID")
        finish(root, entry["entry_id"], reservation, "aborted", after=after, recovery=recovery)
        return {"status": "aborted", "recovery": recovery}
    except BaseException as exc:
        finish(root, entry["entry_id"], reservation, "pending", error=str(exc))
        raise
