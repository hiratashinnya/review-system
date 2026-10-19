"""symlink を再検査して ledger 文書を読み、原子的に置き換える。"""

import os
from pathlib import Path

from .paths_guard import FeedbackPathError


def read_text(path: Path) -> str:
    if path.is_symlink():
        raise FeedbackPathError(f"読み込み直前の再検査で symlink を検知: {path}")
    if not path.is_file():
        raise FeedbackPathError(f"通常ファイルではない: {path}")
    return path.read_text(encoding="utf-8")


def write_text_atomic(path: Path, text: str) -> None:
    """同じディレクトリの一時ファイル経由で置き換える。

    symlink 再検査は best-effort で原子的ではない（karte の K-04 と同じ脅威モデル）。
    """
    if path.is_symlink():
        raise FeedbackPathError(f"書込直前の再検査で symlink を検知（TOCTOU 疑い）: {path}")
    if path.exists() and not path.is_file():
        raise FeedbackPathError(f"書込先が通常ファイルではない: {path}")
    temporary = path.with_name(path.name + ".tmp")
    if temporary.is_symlink():
        raise FeedbackPathError(f"一時ファイル名が symlink として存在する: {temporary}")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)
