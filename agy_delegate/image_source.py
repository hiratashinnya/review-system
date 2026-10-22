"""画像取得元を記述子で保持し、検査した実体と同じ記述子から読み出す。"""

import os
import stat
from contextlib import contextmanager
from pathlib import PurePath

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK


def fingerprint(directory_fd: int) -> dict:
    info = os.fstat(directory_fd)
    return {"device": info.st_dev, "inode": info.st_ino}


@contextmanager
def held_directory(path, error: str, *, dir_fd: int | None = None, missing_ok: bool = False):
    """リンクを辿らずに開いた記述子を保持する。missing_ok の不在は None を渡す。"""
    try:
        descriptor = os.open(path, DIRECTORY_FLAGS, dir_fd=dir_fd)
    except FileNotFoundError:
        if not missing_ok:
            raise ValueError(error) from None
        descriptor = None
    except OSError:
        raise ValueError(error) from None
    try:
        yield descriptor
    finally:
        if descriptor is not None:
            os.close(descriptor)


def read_images(directory_fd: int) -> dict[str, bytes]:
    """画像名ごとに、開いた記述子から1回だけ読んだ内容を返す（ハッシュ取得と書出しの共通入力）。"""
    return {name: _read_regular(directory_fd, name) for name in os.listdir(directory_fd)
            if PurePath(name).suffix.lower() in IMAGE_SUFFIXES}


def _read_regular(directory_fd: int, name: str) -> bytes:
    try:
        descriptor = os.open(name, FILE_FLAGS, dir_fd=directory_fd)
    except OSError:
        raise ValueError("image_symlink_or_nonfile") from None
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("image_symlink_or_nonfile")
        return stream.read()
