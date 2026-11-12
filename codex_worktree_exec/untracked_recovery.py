"""Trusted reversible quarantine of rejected generated and temporary inputs."""
import argparse
import subprocess
import tempfile
from pathlib import Path
from .untracked_policy import classify_untracked, regular_unlinked

RECOVERABLE = frozenset({
    "foreign_cache", "stale_cache", "unsafe_cache", "unsupported_cache_format",
    "coverage_output", "tool_state", "unapproved_tmp",
})


def candidates(worktree: Path) -> list[tuple[str, Path]]:
    root = worktree.resolve()
    names = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--others", "-z"],
        check=True, capture_output=True,
    ).stdout
    source_bytes, selected = {}, []
    for raw in filter(None, names.split(b"\0")):
        relative = Path(raw.decode("utf-8"))
        if relative.is_absolute() or ".." in relative.parts:
            continue
        path = root / relative
        if not regular_unlinked(path):
            continue
        category = classify_untracked(root, relative.as_posix(), source_bytes)
        if category in RECOVERABLE:
            selected.append((category, relative))
    return sorted(selected, key=lambda item: item[1].as_posix())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worktree", type=Path, default=Path.cwd())
    parser.add_argument("--quarantine-parent", type=Path, default=Path(tempfile.gettempdir()))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    root = args.worktree.resolve()
    parent = args.quarantine_parent.resolve()
    if parent.is_relative_to(root):
        raise ValueError("quarantine directory must be outside worktree")
    selected = candidates(root)
    for category, relative in selected:
        print(f"{'move' if args.apply else 'would move'} {relative} ({category})")
    if not args.apply or not selected:
        print(f"untracked recovery count={len(selected)} mode={'apply' if args.apply else 'dry-run'}")
        return 0
    quarantine = Path(tempfile.mkdtemp(prefix="review-system-quarantine-", dir=parent))
    print(f"quarantine directory: {quarantine}", flush=True)
    for category, relative in selected:
        original = root / relative
        if not regular_unlinked(original):
            raise ValueError(f"source changed during recovery; preserved: {relative}")
        destination = quarantine / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        original.rename(destination)  # Atomic; EXDEV fails without deleting source.
        if not regular_unlinked(destination):
            raise ValueError(f"quarantined path unsafe; inspect: {destination}")
    print(f"untracked recovery count={len(selected)} mode=apply; files preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
