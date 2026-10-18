"""Read and write karte files without following a final-component symlink."""

import errno
import os
from pathlib import Path

from .path_errors import KartePathError


def read_text(path: Path) -> str:
    if path.is_symlink():
        raise KartePathError(f"読み込み直前の再検査で symlink を検知: {path}")
    if not path.is_file():
        raise KartePathError(f"通常ファイルではない: {path}")
    return path.read_text(encoding="utf-8")


def _open_writeonly(path: Path, flags: int, mode: int | None = None) -> int:
    try:
        if mode is None:
            return os.open(path, flags)
        return os.open(path, flags, mode)
    except OSError as exc:
        if exc.errno in (errno.EEXIST, errno.ELOOP):
            raise KartePathError(f"symlink または既存パスを拒否: {path}: {exc}") from exc
        raise


def write_text_atomic(path: Path, text: str) -> None:
    """一時ファイルを安全に作成して書き、同じディレクトリで原子的に置き換える。

    再検査は維持し、一時ファイルの検査と open は ``O_EXCL|O_NOFOLLOW`` を付けた
    ``os.open`` で行う。``O_NOFOLLOW`` は最終要素だけに効くため、親要素の symlink 拒否は
    :func:`resolve_within_repo` と呼び出し元のパスガードに依存する。
    """
    if path.is_symlink():
        raise KartePathError(f"書込直前の再検査で symlink を検知: {path}")
    if path.exists() and not path.is_file():
        raise KartePathError(f"書込先が通常ファイルではない: {path}")
    tmp_path = path.with_name(path.name + ".tmp")
    if tmp_path.is_symlink():
        raise KartePathError(f"一時ファイル名が symlink として存在する: {tmp_path}")

    fd = None
    created = False
    try:
        fd = _open_writeonly(
            tmp_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o666,
        )
        created = True
        handle = os.fdopen(fd, "w", encoding="utf-8")
        fd = None
        with handle:
            handle.write(text)
        os.replace(tmp_path, path)
        created = False
    finally:
        if fd is not None:
            os.close(fd)
        if created:
            try:
                tmp_path.unlink()
            except OSError:
                pass


def append_text(path: Path, text: str) -> None:
    """既存ブロックを書き換えずに末尾へ追記する（Attempt/Result は追記のみ）。

    再検査は維持し、対象の検査と open は ``O_NOFOLLOW`` を付けた ``os.open`` で行う。
    ``O_NOFOLLOW`` は最終要素だけに効くため、親要素の symlink 拒否は
    :func:`resolve_within_repo` と呼び出し元のパスガードに依存する。
    """
    if path.is_symlink():
        raise KartePathError(f"追記直前の再検査で symlink を検知: {path}")
    if not path.is_file():
        raise KartePathError(f"追記先が通常ファイルではない: {path}")

    fd = _open_writeonly(path, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
    try:
        handle = os.fdopen(fd, "a", encoding="utf-8")
        fd = None
        with handle:
            handle.write(text)
    finally:
        if fd is not None:
            os.close(fd)
