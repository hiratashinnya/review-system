"""工程artifact本体はcommit済みの内容だけを下流へ渡す。"""
import subprocess
from pathlib import Path


def read_committed_artifact(path: Path, root: Path) -> bytes:
    resolved = root.resolve()
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError("artifact path is symlink")
    relative = path.resolve().relative_to(resolved)
    content = path.read_bytes()
    result = subprocess.run(
        ["git", "-C", str(root), "show", f"HEAD:{relative.as_posix()}"],
        capture_output=True, check=True,
    )
    if content != result.stdout:
        raise ValueError("artifact has uncommitted changes")
    return content
