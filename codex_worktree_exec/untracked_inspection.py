"""Read-only untracked inspection, including ignored files."""
import subprocess
from pathlib import Path
from .untracked_diagnostics import describe
from .untracked_policy import classify_untracked


def verify_untracked_sources(worktree: Path) -> None:
    root = worktree.resolve()
    prefix = ["git", "-C", str(root)]
    result = subprocess.run(prefix + ["ls-files", "--others", "-z"],
                            check=True, capture_output=True)
    linked = subprocess.run(prefix + ["worktree", "list", "--porcelain", "-z"],
                            check=True, capture_output=True).stdout.split(b"\0")
    roots = {Path(item[9:].decode()).resolve() for item in linked
             if item.startswith(b"worktree ")} - {root}
    cache_sources, violations = {}, []
    for raw in filter(None, result.stdout.split(b"\0")):
        name = raw.decode("utf-8")
        path = root / name
        if path.resolve() in roots and not path.is_symlink():
            continue
        category = classify_untracked(root, name, cache_sources)
        if category:
            violations.append((category, name))
    if violations:
        raise ValueError(describe(violations))
