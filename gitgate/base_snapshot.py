"""Conflict-safe snapshot without write-tree; includes unmerged index stages."""

import hashlib
import os
import stat
from pathlib import Path
from .base_error import require
from .base_git import git, merge_head, output


def index_records(workspace):
    records = []
    for raw in git(workspace, "ls-files", "--stage", "-z").stdout.split(b"\0"):
        if raw:
            metadata, path = raw.split(b"\t", 1)
            mode, oid, stage = metadata.decode("ascii").split()
            records.append([mode, oid, int(stage), os.fsdecode(path)])
    return records


def snapshot(workspace):
    digest = hashlib.sha256()
    listed = git(workspace, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
    for raw in sorted(set(listed.stdout.split(b"\0")) - {b""}):
        path = Path(workspace) / os.fsdecode(raw)
        require(all(not parent.is_symlink() for parent in path.parents
                    if parent != Path(workspace)), "BASE_CONTENT_SYMLINK_PARENT")
        if not path.exists() and not path.is_symlink():
            digest.update(raw + b"\0deleted\0")
            continue
        metadata = path.lstat()
        require(stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode),
                "BASE_CONTENT_TYPE_INVALID")
        content = os.fsencode(os.readlink(path)) if path.is_symlink() else path.read_bytes()
        digest.update(raw + b"\0" + str(metadata.st_mode).encode() + b"\0")
        digest.update(str(len(content)).encode() + b"\0" + content + b"\0")
    return {"head": output(workspace, "rev-parse", "HEAD"),
            "merge_head": merge_head(workspace), "index": index_records(workspace),
            "content_sha256": digest.hexdigest(),
            "status": os.fsdecode(git(workspace, "status", "--porcelain=v1", "-z").stdout)}


def conflict_paths(records):
    return sorted({record[3] for record in records if record[2] != 0})
