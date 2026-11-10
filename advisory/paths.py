"""Path safety and Linux advisory lock for serialized local writes."""

import fcntl
import os
import stat
from contextlib import contextmanager
from pathlib import Path

LEDGER = Path(".ai/advisory/ledger")


def directory(root: Path, create: bool = False) -> Path:
    root = Path(root).resolve()
    cursor = root
    for part in LEDGER.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("symlink in advisory ledger path")
    if create:
        cursor.mkdir(parents=True, exist_ok=True)
    if cursor.exists() and not cursor.is_dir():
        raise ValueError("advisory ledger path is not a directory")
    return cursor


def record_path(root: Path, document_id: str) -> Path:
    if not document_id.startswith("ADV-") or "/" in document_id or "\\" in document_id:
        raise ValueError("unsafe advisory ID")
    path = directory(root) / (document_id + ".toml")
    if path.is_symlink():
        raise ValueError("symlink advisory entry")
    return path


@contextmanager
def writer_lock(root: Path):
    folder = directory(root, create=True)
    handle = os.open(folder / ".writer.lock",
                     os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        mode = os.fstat(handle)
        if not stat.S_ISREG(mode.st_mode) or mode.st_nlink != 1:
            raise ValueError("unsafe advisory writer lock")
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield
    finally:
        os.close(handle)
