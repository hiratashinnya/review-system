"""Internal path handling for the karte package."""

import os
from pathlib import Path

from .path_errors import KartePathError

def read_text(path: Path) -> str:
    if path.is_symlink():
        raise KartePathError(f"読み込み直前の再検査で symlink を検知: {path}")
    if not path.is_file():
        raise KartePathError(f"通常ファイルではない: {path}")
    return path.read_text(encoding="utf-8")

def write_text_atomic(path: Path, text: str) -> None:
    """同一ディレクトリ内の一時ファイル経由で置き換える（``os.replace`` は原子的）。

    書込直前に symlink 化していないかを再検査する。**この再検査は best-effort であって
    原子的ではない**（K-04・保証範囲の正直な記述）:

    * :meth:`Path.write_text` は symlink を**追跡する**。``is_symlink()`` による検査と
      実際の ``open`` の間に対象を symlink へ差し替えられれば、書込はその先を追う
      ——**window が存在する**。ここは「TOCTOU 対策」と呼べる強さを持たない。
    * 現行の脅威モデル（書込先は ``tmp/_karte`` 直下に限定・repo-root から対象までの
      各構成要素は :func:`resolve_within_repo` で非 symlink を確認済み・同一 uid の
      プロセスしか居ない）では、この window を悪用できる経路は無い。それでも
      「無い」のは環境の性質であって、この関数の保証ではない。
    * 比較対象として、``dsv2/cleantmp.py`` の ``_reverify_before_delete`` の方が厳密である
      ——削除の直前に**同じガードを再実行**して window を詰めている。こちらは検査後に
      別の API（``open``）で対象を開き直すため、同じ強さには達していない。

    **Issue #318 で ``os.open(..., O_NOFOLLOW)`` を使う実装へ厳密化する予定**
    （open 自体に symlink 非追跡を強制し、検査と使用の間の window を無くす）。
    """
    if path.is_symlink():
        raise KartePathError(f"書込直前の再検査で symlink を検知（TOCTOU 疑い）: {path}")
    if path.exists() and not path.is_file():
        raise KartePathError(f"書込先が通常ファイルではない: {path}")
    tmp_path = path.with_name(path.name + ".tmp")
    if tmp_path.is_symlink():
        raise KartePathError(f"一時ファイル名が symlink として存在する: {tmp_path}")
    tmp_path.write_text(text, encoding="utf-8")
    os.replace(tmp_path, path)

def append_text(path: Path, text: str) -> None:
    """既存ブロックを書き換えずに末尾へ追記する（Attempt/Result は追記のみ）。

    追記直前の symlink 再検査は :func:`write_text_atomic` と同じ**best-effort**である
    （K-04）。``open(path, "a")`` は symlink を追跡するため、``is_symlink()`` 検査と
    ``open`` の間に差し替えられれば追従する window が残る。現行の脅威モデルで悪用可能な
    経路が無い点、``dsv2/cleantmp.py`` の ``_reverify_before_delete`` の方が厳密である点、
    **Issue #318 で ``O_NOFOLLOW`` により厳密化する予定**である点も同じ。
    """
    if path.is_symlink():
        raise KartePathError(f"追記直前の再検査で symlink を検知（TOCTOU 疑い）: {path}")
    if not path.is_file():
        raise KartePathError(f"追記先が通常ファイルではない: {path}")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text)
