"""Internal path handling for the karte package."""

import os
import stat
import fcntl
from contextlib import contextmanager
from pathlib import Path

from .path_errors import (
    ACTIVE_FILENAME,
    KARTE_DIRNAME,
    KARTE_FILENAME_FMT,
    TMP_DIRNAME,
    KarteMissing,
    KartePathError,
    validate_issue,
)
from .path_guard import resolve_within_repo
from .path_roots import _resolved_root

@contextmanager
def writer_lock(repo_root):
    """Serialize every karte CLI mutation of the ledger on one stable lock inode."""
    directory = karte_dir(repo_root, create=True)
    fd = os.open(directory / ".writer.lock",
                 os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise KartePathError("カルテ writer lock は単一の通常ファイルでなければならない")
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)

def karte_dir(repo_root, *, create: bool = False) -> Path:
    """``<repo-root>/tmp/_karte`` を返す（``create`` で不在時に作成）。"""
    root = _resolved_root(repo_root)
    tmp = root / TMP_DIRNAME
    if tmp.is_symlink():
        raise KartePathError(
            f"tmp ディレクトリ自体が symlink: {tmp}（repo 外へ誘導されうるため拒否）"
        )
    if not tmp.exists():
        if not create:
            raise KarteMissing(f"tmp ディレクトリが無い: {tmp}")
        tmp.mkdir(parents=True)
    if not tmp.is_dir():
        raise KartePathError(f"tmp がディレクトリでない: {tmp}")

    target = tmp / KARTE_DIRNAME
    if target.is_symlink():
        raise KartePathError(
            f"カルテ置き場が symlink: {target}（symlink 越しの書込は拒否）"
        )
    if not target.exists():
        if not create:
            raise KarteMissing(f"カルテ置き場が無い: {target}")
        target.mkdir(parents=True)
    if not target.is_dir():
        raise KartePathError(f"カルテ置き場がディレクトリでない: {target}")
    return target

def karte_path(issue, repo_root, *, create_dir: bool = False) -> Path:
    """``<repo-root>/tmp/_karte/issue-<N>.md`` を返す（ガード5）。"""
    number = validate_issue(issue)
    directory = karte_dir(repo_root, create=create_dir)
    path = directory / KARTE_FILENAME_FMT.format(issue=number)
    checked = resolve_within_repo(path, repo_root)
    if checked.parent != directory.resolve():
        raise KartePathError(f"カルテ置き場の直下ではない: {checked}")
    if checked.is_symlink():
        raise KartePathError(f"カルテ本体が symlink: {checked}")
    return checked

def active_path(repo_root, *, create_dir: bool = False) -> Path:
    """進行ポインタ ``tmp/_karte/active.json`` を返す。

    ``agent_id`` を結合キーにしない（方針転換で新しいコンテキストへ引き継ぐと途切れるため）。
    """
    directory = karte_dir(repo_root, create=create_dir)
    path = directory / ACTIVE_FILENAME
    if path.is_symlink():
        raise KartePathError(f"進行ポインタが symlink: {path}")
    return path
