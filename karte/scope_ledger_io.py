"""固定されたカルテ置き場から申告 scope 原本を読む。"""

import os
import stat

from .path_errors import KartePathError
from .scope_directory import open_scope_directory


def scope_entry(path, directory):
    """不在は None、通常ファイルは stat を返し、それ以外は拒否する。"""
    directory.check()
    try:
        info = os.stat(path.name, dir_fd=directory.fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise KartePathError(f"申告 scope の原本を検査できない: {path}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode):
        raise KartePathError(f"申告 scope の原本に symlink を検知: {path}")
    if not stat.S_ISREG(info.st_mode):
        raise KartePathError(f"申告 scope の原本が通常ファイルではない: {path}")
    return info


def read_scope_text(path, directory=None):
    """固定 dirfd と O_NOFOLLOW で読み、不在のみ None を返す。"""
    if directory is None:
        with open_scope_directory(path) as owned:
            return read_scope_text(path, owned)
    before = scope_entry(path, directory)
    if before is None:
        return None
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory.fd)
    except OSError as exc:
        raise KartePathError(f"申告 scope の原本を開けない: {path}: {exc}") from exc
    try:
        after = os.fstat(fd)
        if not stat.S_ISREG(after.st_mode) or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise KartePathError(f"申告 scope の原本が操作中に変更された: {path}")
        directory.check()
        with os.fdopen(fd, "r", encoding="utf-8") as stream:
            fd = None
            try:
                text = stream.read()
            except UnicodeDecodeError as exc:
                raise KartePathError(f"UTF-8 として読めない: {path}（{exc.reason}）") from None
        directory.check()
        return text
    finally:
        if fd is not None:
            os.close(fd)
