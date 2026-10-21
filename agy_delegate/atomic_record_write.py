"""実行・会話記録を private な一時ファイルから原子的に置換する。"""

import errno
import os
import uuid
from os import open as open_directory
from pathlib import Path


def atomic_private_write(path: Path, encoded: str) -> None:
    _reject_symlink(path)
    temporary = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    descriptor = os.open(temporary, flags, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        _reject_symlink(path)
        os.replace(temporary, path)
        _sync_parent_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _reject_symlink(path: Path) -> None:
    if path.is_symlink():
        raise OSError(errno.ELOOP, "record_path_symlink")


def _sync_parent_directory(directory: Path) -> None:
    """置換確定後の親ディレクトリ同期は必須とし、失敗は呼出元へ伝播する。"""
    descriptor = open_directory(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
