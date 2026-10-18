"""feedback、ledger、triage、draft の各パスを repo-root 配下に解決する。"""

from pathlib import Path

from .paths_guard import (
    DRAFT_DIRNAME,
    FEEDBACK_DIRNAME,
    LEDGER_SUBDIR,
    QUEUE_SUBDIR,
    TRIAGE_SUBDIR,
    FeedbackMissing,
    FeedbackPathError,
    resolve_within_repo,
)


def feedback_dir(root, *, create: bool = False) -> Path:
    """台帳ディレクトリを返す（``create`` のときだけ作成する）。"""
    target = resolve_within_repo(FEEDBACK_DIRNAME, root)
    if not target.exists():
        if not create:
            raise FeedbackMissing(f"台帳の置き場が無い: {target}")
        target.mkdir(parents=True)
    if not target.is_dir():
        raise FeedbackPathError(f"台帳の置き場がディレクトリでない: {target}")
    return target


def subdir(root, name: str, *, create: bool = False) -> Path:
    """固定された台帳サブディレクトリを返す。"""
    if name not in (LEDGER_SUBDIR, QUEUE_SUBDIR, TRIAGE_SUBDIR):
        raise FeedbackPathError(f"未知のサブディレクトリ: {name!r}")
    parent = feedback_dir(root, create=create)
    target = parent / name
    if target.is_symlink():
        raise FeedbackPathError(f"サブディレクトリが symlink: {target}")
    if not target.exists():
        if not create:
            raise FeedbackMissing(f"サブディレクトリが無い: {target}")
        target.mkdir(parents=True)
    if not target.is_dir():
        raise FeedbackPathError(f"サブディレクトリでない: {target}")
    return target


def document_path(root, name: str, filename: str, *, create_dir: bool = False) -> Path:
    """固定された台帳サブディレクトリ直下の文書パスを返す。"""
    directory = subdir(root, name, create=create_dir)
    checked = resolve_within_repo(directory / filename, root)
    if checked.parent != directory.resolve():
        raise FeedbackPathError(f"サブディレクトリの直下ではない: {checked}")
    if checked.is_symlink():
        raise FeedbackPathError(f"文書が symlink: {checked}")
    return checked


def draft_path(root, given) -> Path:
    """repo-root 配下にある draft パスを検査して返す。"""
    checked = resolve_within_repo(given, root)
    if checked.is_symlink():
        raise FeedbackPathError(f"下書きが symlink: {checked}")
    if not checked.is_file():
        raise FeedbackMissing(f"下書きが無い: {checked}")
    return checked


def draft_dir(root, *, create: bool = False) -> Path:
    """一時 draft ディレクトリを返す（``create`` のときだけ作成する）。"""
    target = resolve_within_repo(DRAFT_DIRNAME, root)
    if not target.exists():
        if not create:
            raise FeedbackMissing(f"下書き置き場が無い: {target}")
        target.mkdir(parents=True)
    if not target.is_dir():
        raise FeedbackPathError(f"下書き置き場がディレクトリでない: {target}")
    return target
