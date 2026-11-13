"""Trusted cache prune: non-destructive quarantine outside the checkout."""
import argparse
import subprocess
import tempfile
from pathlib import Path
from .safe_quarantine import index_guard, move_checked
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


def _allowed(root: Path, relative: Path) -> bool:
    return (relative.parent.name == "__pycache__" and relative.suffix == ".pyc"
            and regular_unlinked(root / relative))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worktree", type=Path, default=Path.cwd())
    parser.add_argument("--quarantine-parent", type=Path, default=Path(tempfile.gettempdir()))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    root, parent = args.worktree.resolve(), args.quarantine_parent.resolve()
    if parent.is_relative_to(root):
        raise ValueError("quarantine must be outside worktree")
    files = candidates(root)
    for path in files:
        print(("quarantine " if args.apply else "would quarantine ") + str(path))
    if args.apply and files:
        directory = Path(tempfile.mkdtemp(prefix="review-system-cache-", dir=parent))
        print(f"quarantine directory: {directory}", flush=True)
        with index_guard(root):
            for path in files:
                relative = path.relative_to(root)
                move_checked(root, relative, directory / relative, _allowed)
    print(f"cache prune count={len(files)} mode={'apply' if args.apply else 'dry-run'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
