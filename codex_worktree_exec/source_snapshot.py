"""入力snapshot後のsource変更を拒否し、工程artifact commitだけを許可する。"""
import re
import subprocess
import tomllib
from pathlib import Path
from issue_envelope.model import normalize
from issue_envelope.placement import validate_placement


def verify_source_snapshot(worktree: Path, oid: str, issue: int) -> None:
    """祖先であっても通常sourceが1つ変わればstaleとして拒否する。"""
    if not isinstance(oid, str) or not re.fullmatch(r"[0-9a-f]{40}", oid):
        raise ValueError("invalid source snapshot_oid")
    prefix = ["git", "-C", str(worktree)]
    subprocess.run(prefix + ["merge-base", "--is-ancestor", oid, "HEAD"],
                   check=True, capture_output=True, text=True)
    result = subprocess.run(prefix + ["diff", "--name-only", "-z", oid, "--"],
                            check=True, capture_output=True)
    for raw in filter(None, result.stdout.split(b"\0")):
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
