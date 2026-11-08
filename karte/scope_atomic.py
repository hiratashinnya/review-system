"""申告 scope 原本と世代別 backup を固定 dirfd 内で保存する。"""

import os
import secrets
from contextlib import contextmanager

from .path_errors import KartePathError
from .scope_ledger_io import read_scope_text
from .utf8_text import require_utf8_encodable


@contextmanager
def _temporary_text(path, directory, text):
    require_utf8_encodable(text, path)
    directory.check()
    name = f".{path.name}.{secrets.token_hex(12)}.tmp"
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o666, dir_fd=directory.fd)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            fd = None
            stream.write(text)
        directory.check()
        yield name
    finally:
        if fd is not None:
            os.close(fd)
        try:
            os.unlink(name, dir_fd=directory.fd)
        except FileNotFoundError:
            pass


def write_scope_text(path, directory, text, *, expected):
    """原本の内容が読取時と一致するときだけ固定 dirfd 内で原子的に更新する。"""
    if read_scope_text(path, directory) != expected:
        raise KartePathError(f"申告 scope の原本が操作中に変更された: {path}")
    with _temporary_text(path, directory, text) as name:
        if read_scope_text(path, directory) != expected:
            raise KartePathError(f"申告 scope の原本が操作中に変更された: {path}")
        directory.check()
        try:
            os.replace(name, path.name, src_dir_fd=directory.fd, dst_dir_fd=directory.fd)
        except (TypeError, NotImplementedError) as exc:
            raise KartePathError("申告 scope の原本を安全に更新する OS 機能がない") from exc
        directory.check()


def write_scope_backup(path, directory, text):
    """完全な backup を空いている世代名へ上書きせず公開する。"""
    with _temporary_text(path, directory, text) as name:
        generation = 0
        while True:
            suffix = ".bak" if generation == 0 else f".bak.{generation}"
            directory.check()
            try:
                os.link(name, path.name + suffix, src_dir_fd=directory.fd, dst_dir_fd=directory.fd,
                        follow_symlinks=False)
            except FileExistsError:
                generation += 1
                continue
            except (TypeError, NotImplementedError) as exc:
                raise KartePathError("申告 scope の backup を安全に保存する OS 機能がない") from exc
            directory.check()
            return
