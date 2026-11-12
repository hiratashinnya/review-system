"""Explicit trusted deletion, limited to regular untracked __pycache__ pycs."""
import argparse
import subprocess
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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worktree", type=Path, default=Path.cwd())
    parser.add_argument("--apply", action="store_true")
    options = parser.parse_args(argv)
    files = candidates(options.worktree)
    for path in files:
        if options.apply:
            if not regular_unlinked(path):
                raise ValueError("cache changed during prune; refusing")
            path.unlink()
        print(("removed " if options.apply else "would remove ") + str(path))
    print(f"cache prune count={len(files)} mode={'apply' if options.apply else 'dry-run'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
