"""cohort file の no-follow bounded 読取と inode/所有権の安定検査。"""

import os
import stat

from .cohort_fields import MAX_FILE_BYTES
from .image_source import FILE_FLAGS


def private_file_bytes(directory_fd: int, name: str) -> tuple[bytes, tuple]:
    """同じ記述子の前後 fingerprint と regular0600/同UIDを検査する。"""
    try:
        descriptor = os.open(name, FILE_FLAGS, dir_fd=directory_fd)
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            _check_file(before)
            content = stream.read(MAX_FILE_BYTES + 1)
            after = os.fstat(stream.fileno())
            if len(content) > MAX_FILE_BYTES:
                raise ValueError("cohort_file_too_large")
            if file_identity(before) != file_identity(after) or len(content) != before.st_size:
                raise ValueError("cohort_file_changed")
            return content, file_identity(after)
    except OSError:
        raise ValueError("cohort_file_unavailable") from None


def file_identity(info) -> tuple:
    return (info.st_dev, info.st_ino, info.st_uid, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def require_no_marker(directory_fd: int, wid: str) -> None:
    """marker は種別/owner を問わず存在だけで失敗にする。"""
    try:
        os.stat(f"{wid}.publishing", dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    except OSError:
        raise ValueError("cohort_marker_unreadable") from None
    raise ValueError("cohort_publication_pending")


def _check_file(info) -> None:
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("cohort_file_type_invalid")
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
        raise ValueError("cohort_file_owner_or_mode_invalid")
    if info.st_size > MAX_FILE_BYTES:
        raise ValueError("cohort_file_too_large")
