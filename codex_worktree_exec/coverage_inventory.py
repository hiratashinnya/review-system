"""Fail-closed HEAD parity guard for untracked test/source inputs."""
import subprocess
from pathlib import Path


def require_head_test_source_inventory(root: Path) -> None:
    """A HEAD-based plain checkout cannot run added local tests/source.

    Include ignored files: gitignore and per-clone exclude are not approval.
    Generated non-source output outside tests does not affect test discovery.
    """
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--others", "-z"],
        check=True, capture_output=True,
    )
    unsafe = []
    for raw in filter(None, result.stdout.split(b"\0")):
        relative = Path(raw.decode("utf-8", "surrogateescape"))
        if ((relative.parts and relative.parts[0] == "tests")
                or relative.suffix == ".py"):
            unsafe.append(relative.as_posix())
    if unsafe:
        sample = ", ".join(sorted(unsafe)[:5])
        raise ValueError(
            f"coverage input inventory differs from HEAD: untracked tests/source "
            f"count={len(unsafe)} examples=[{sample}]"
        )
