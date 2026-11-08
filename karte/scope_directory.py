"""申告 scope 用のディレクトリを記述子で固定する。"""

import os
import stat
from contextlib import contextmanager

from .path_errors import KarteMissing, KartePathError

_DIR_FD_SUPPORTED = all(
    operation in os.supports_dir_fd for operation in (os.open, os.stat, os.link, os.unlink, os.rename, os.mkdir)
) and all(operation in os.supports_follow_symlinks for operation in (os.stat, os.link))


def _flags():
    required = ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK")
    if not _DIR_FD_SUPPORTED or any(not getattr(os, name, 0) for name in required):
        raise KartePathError("申告 scope の原本を安全に扱うための OS 機能がない")
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK


def _identity(info):
    return info.st_dev, info.st_ino


class ScopeDirectory:
    def __init__(self, root, fds):
        self.root = root
        self.root_fd, self.tmp_fd, self.fd = fds

    def check(self):
        """開いたディレクトリが現在の置き場と一致しなければ拒否する。"""
        try:
            current = (
                os.stat(self.root, follow_symlinks=False),
                os.stat("tmp", dir_fd=self.root_fd, follow_symlinks=False),
                os.stat("_karte", dir_fd=self.tmp_fd, follow_symlinks=False),
            )
            opened = tuple(os.fstat(fd) for fd in (self.root_fd, self.tmp_fd, self.fd))
        except OSError as exc:
            raise KartePathError(f"申告 scope の置き場を検査できない: {exc}") from exc
        if any(not stat.S_ISDIR(item.st_mode) for item in current) or any(
            _identity(left) != _identity(right) for left, right in zip(current, opened)
        ):
            raise KartePathError("申告 scope の置き場が操作中に変更された")


def _open_child(parent, name, flags, *, create):
    try:
        return os.open(name, flags, dir_fd=parent)
    except FileNotFoundError:
        if not create:
            raise KarteMissing(f"申告 scope の置き場が無い: {name}") from None
    try:
        os.mkdir(name, dir_fd=parent)
    except FileExistsError:
        pass
    return os.open(name, flags, dir_fd=parent)


@contextmanager
def open_scope_directory(path, *, create=False):
    """repo-root → tmp → _karte を no-follow で開き、操作中は fd を保持する。"""
    root = path.parent.parent.parent
    fds = []
    try:
        flags = _flags()
        fds.append(os.open(root, flags))
        fds.append(_open_child(fds[-1], "tmp", flags, create=create))
        fds.append(_open_child(fds[-1], "_karte", flags, create=create))
        directory = ScopeDirectory(root, fds)
        directory.check()
        yield directory
    except OSError as exc:
        raise KartePathError(f"申告 scope の置き場を開けない: {exc}") from exc
    finally:
        for fd in reversed(fds):
            os.close(fd)
