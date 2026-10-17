"""snapshot後は同Issue artifactとtrusted caller承認済みの正確なbytesだけを許可する。"""
import hashlib
import re
import subprocess
import tomllib
from pathlib import Path
from issue_envelope.model import normalize
from issue_envelope.placement import validate_placement
from .committed_artifact import read_committed_artifact


def _approved_paths(worktree: Path, changes) -> set[str]:
    if changes is None:
        return set()
    if not isinstance(changes, dict):
        raise ValueError("source_changes must map exact paths to sha256 or null")
    for name, digest in changes.items():
        if (not isinstance(name, str) or not name or Path(name).is_absolute()
                or any(part in ("..", ".git") for part in Path(name).parts)
                or Path(name).as_posix() != name):
            raise ValueError("invalid approved source path")
        path = worktree / name
        if any(part.is_symlink() for part in (path, *path.parents)):
            raise ValueError("approved source is symlink")
        if digest is None:
            committed = subprocess.run(["git", "-C", str(worktree), "ls-tree", "HEAD", "--", name],
                                       capture_output=True, check=True)
            if path.exists() or committed.stdout:
                raise ValueError("approved deletion is not committed")
        elif (not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
              or hashlib.sha256(read_committed_artifact(path, worktree)).hexdigest() != digest):
            raise ValueError("approved source digest mismatch")
    return set(changes)


def verify_source_snapshot(worktree: Path, oid: str, issue: int, source_changes=None) -> None:
    """通常sourceはcallerが承認したpath/digest集合から1byteでも外れれば拒否する。"""
    if not isinstance(oid, str) or not re.fullmatch(r"[0-9a-f]{40}", oid):
        raise ValueError("invalid source snapshot_oid")
    prefix = ["git", "-C", str(worktree)]
    approved = _approved_paths(worktree, source_changes)
    subprocess.run(prefix + ["merge-base", "--is-ancestor", oid, "HEAD"],
                   check=True, capture_output=True, text=True)
    result = subprocess.run(prefix + ["diff", "--name-only", "-z", oid, "--"],
                            check=True, capture_output=True)
    for raw in filter(None, result.stdout.split(b"\0")):
        if raw.decode("utf-8") in approved:
            continue
        path = worktree / raw.decode("utf-8")
        if path.is_symlink() or not path.is_file():
            raise ValueError("source snapshot changed/deleted")
        try:
            data = normalize(tomllib.loads(path.read_text(encoding="utf-8")))
            validate_placement(path, data, worktree)
        except (ValueError, OSError) as error:
            raise ValueError("source snapshot changed outside canonical artifacts") from error
        if data["issue"] != issue:
            raise ValueError("other issue source changed")
        read_committed_artifact(path, worktree)
