"""Explicit trusted deletion, limited to regular untracked __pycache__ pycs."""
import argparse
import os
import stat
import subprocess
import tempfile
from pathlib import Path
from .untracked_policy import regular_unlinked


def candidates(worktree: Path) -> list[Path]:
    root = worktree.resolve()
    names = subprocess.run(["git", "-C", str(root), "ls-files", "--others", "-z"],
                           capture_output=True, check=True).stdout
    result = []
    for raw in filter(None, names.split(b"\0")):
        relative = Path(raw.decode("utf-8"))
        path = root / relative
        if (not relative.is_absolute() and ".." not in relative.parts
                and relative.parent.name == "__pycache__"
                and relative.suffix == ".pyc" and regular_unlinked(path)
                and path.resolve().is_relative_to(root)):
            result.append(path)
    return sorted(result)


def identity(path: Path) -> tuple:
    s = path.stat(follow_symlinks=False)
    return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_mode


def prune_one(path: Path) -> None:
    if not regular_unlinked(path):
        raise ValueError("cache changed during prune; refusing")
    expected = identity(path)
    descriptor, temporary = tempfile.mkstemp(prefix=".cache-prune-", dir=path.parent)
    os.close(descriptor)
    staged = Path(temporary)
    moved = False
    try:
        os.replace(path, staged)
        moved = True
        actual = identity(staged)
        if not stat.S_ISREG(actual[-1]) or actual != expected:
            if not path.exists() and not path.is_symlink():
                os.replace(staged, path)
            raise ValueError(f"cache changed during prune; preserved at {path if path.exists() else staged}")
        staged.unlink()
    finally:
        if not moved and staged.exists():
            staged.unlink()  # Only our own empty temporary placeholder.


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worktree", type=Path, default=Path.cwd())
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    files = candidates(args.worktree)
    for path in files:
        if args.apply:
            prune_one(path)
        print(("removed " if args.apply else "would remove ") + str(path))
    print(f"cache prune count={len(files)} mode={'apply' if args.apply else 'dry-run'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
