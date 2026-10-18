"""リポジトリ内パスを解決し、危険な入力を拒否する。"""

from __future__ import annotations

import os
from pathlib import Path

FEEDBACK_DIRNAME = ".ai/feedback"
LEDGER_SUBDIR = "ledger"
QUEUE_SUBDIR = "queue"
TRIAGE_SUBDIR = "triage"
DRAFT_DIRNAME = "tmp/_feedback"


class FeedbackPathError(Exception):
    """台帳パスの安全検査に違反したときに送出する。"""


class FeedbackMissing(FeedbackPathError):
    """必須の台帳パスが存在しないときに送出する。"""


def repo_root() -> Path:
    """このパッケージを含むリポジトリの root を返す。"""
    return Path(__file__).resolve().parents[1]


def _resolved_root(root) -> Path:
    resolved = Path(root).resolve()
    if not resolved.is_dir():
        raise FeedbackPathError(f"repo-root がディレクトリでない: {resolved}")
    return resolved


def resolve_within_repo(path, root) -> Path:
    """最終要素が未作成でも使える repo-root 配下の安全なパスを返す。"""
    resolved_root = _resolved_root(root)
    given = Path(path)
    if ".." in given.parts:
        raise FeedbackPathError(f"'..' を含むパスは受け付けない（traversal 拒否）: {given}")
    if not given.is_absolute():
        given = resolved_root / given

    lexical = Path(os.path.normpath(str(given)))
    try:
        relative = lexical.relative_to(resolved_root)
    except ValueError:
        raise FeedbackPathError(
            f"repo-root の外を指している: {lexical}（repo-root={resolved_root}）"
        ) from None

    cursor = resolved_root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise FeedbackPathError(
                f"パス構成要素が symlink: {cursor}（symlink 経由の読み書きは拒否）"
            )

    try:
        lexical.resolve().relative_to(resolved_root)
    except ValueError:
        raise FeedbackPathError(
            f"実体解決の結果 repo-root の外を指した: {lexical}"
        ) from None
    return lexical
