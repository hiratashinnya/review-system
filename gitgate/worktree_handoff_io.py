"""Safe handoff reads and exclusive destination creation."""

import os
import stat
from pathlib import Path
from .worktree_models import WorktreeError

def _read_handoff(source: Path, *, max_bytes: int) -> bytes:
    """``O_NOFOLLOW`` で開き、regular file であることを fd 経由で確かめてから読む。

    ``lstat`` → ``open`` の2段だと間に差し替えられる（TOCTOU）。``O_NOFOLLOW`` は
    「最終要素が symlink なら開かない」を kernel 側で保証し、``fstat`` は**開いた当の
    inode** の種別を返すので、検査と読み取りが同じ実体を指すことが構造的に決まる。
    """
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(str(source), flags)
    except OSError as exc:
        raise WorktreeError("COLLECT_HANDOFF_UNREADABLE", f"{source}: {exc.strerror}") from exc
    try:
        stat_result = os.fstat(fd)
        if not stat.S_ISREG(stat_result.st_mode):
            raise WorktreeError("COLLECT_HANDOFF_NOT_REGULAR_FILE", str(source))
        if stat_result.st_size > max_bytes:
            raise WorktreeError(
                "COLLECT_HANDOFF_TOO_LARGE", f"{stat_result.st_size} > {max_bytes}"
            )
        with os.fdopen(fd, "rb") as handle:
            fd = -1
            return handle.read(max_bytes + 1)
    finally:
        if fd >= 0:
            os.close(fd)


def _write_collected(dest: Path, data: bytes) -> None:
    """``O_CREAT|O_EXCL`` で作る。既存なら ``COLLECT_DEST_EXISTS``（上書きしない＝消さない）。"""
    try:
        fd = os.open(str(dest), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise WorktreeError("COLLECT_DEST_EXISTS", str(dest)) from exc
    except OSError as exc:
        raise WorktreeError("COLLECT_WRITE_ERROR", f"{dest}: {exc.strerror}") from exc
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)


def _ensure_collected_dir(repo_root, relative_dir: str) -> Path:
    base = Path(repo_root).resolve()
    current = base
    for part in relative_dir.split("/"):
        current = current / part
        if current.is_symlink():
            raise WorktreeError("COLLECT_DEST_SYMLINK", str(current))
        if not current.exists():
            current.mkdir(parents=False)
        elif not current.is_dir():
            raise WorktreeError("COLLECT_DEST_NOT_DIR", str(current))
    return current
