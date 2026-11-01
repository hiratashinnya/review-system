"""固定settings候補をnofollow・bounded・同descriptorで読み取る。"""

import os
import stat
from pathlib import Path

MAX_BYTES = 1048576


def validate_settings_path(path: Path) -> None:
    """未知のリンクを辿らず、OSErrorの本文を外へ公開しない呼出境界に渡す。"""
    for part in (*reversed(path.parents), path):
        if stat.S_ISLNK(part.lstat().st_mode):
            raise ValueError("settings_path_symlink")


def read_settings_bytes(path: Path) -> bytes:
    """原bytesは呼出memoryだけに返し、file/size/identity変化を拒否する。"""
    validate_settings_path(path)
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_NONBLOCK"):
        raise ValueError("settings_safe_open_unavailable")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_BYTES:
            raise ValueError("settings_not_bounded_regular")
        raw = stream.read(MAX_BYTES + 1)
        after = os.fstat(stream.fileno())
        fields = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
        if len(raw) > MAX_BYTES or any(getattr(before, key) != getattr(after, key) for key in fields):
            raise ValueError("settings_read_changed")
    return raw
