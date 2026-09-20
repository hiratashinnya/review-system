"""`.ai/feedback/` のパス解決とガード（fail-close）。

書き先の一部（下書きファイルの指定・文書 id）は上流のプロンプト由来＝**信頼できない入力**
として扱う。素直に ``open(path)`` すると ``..`` traversal や symlink 経由でリポジトリ外の
ファイルを読み書きしうるため、「触ってよい形のパスか」を検査してからしか触らない。
ガードの様式は ``karte/paths.py``（Issue #307）と同型で、次の4点をすべて満たさなければ触らない。

  1. 入力パスに ``..`` 構成要素を含まない（**正規化より先に**拒否する。``root/link/../x`` のように
     正規化が symlink を飛ばしてしまう穴を塞ぐため）。
  2. 正規化後のパスが実体解決済み repo-root の配下にある。
  3. repo-root から対象までの各構成要素が symlink でない。
  4. 実体解決後もなお repo-root 配下にある。

**``karte/paths.py`` と違って main worktree へは収束させない**。カルテ（``tmp/_karte/``）は
版管理外の共有台帳なので worktree 間で1つに寄せる必要があったが、``.ai/feedback/`` は
**版管理下のワークツリー内容**であり、linked worktree ではその worktree のチェックアウトを
読み書きするのが正しい（収束させると別ブランチの内容を書き換えてしまう）。

依存仕様: ``karte/paths.py`` docstring（ガード様式）／``dsv2/cleantmp.py`` docstring。
"""

from __future__ import annotations

import fcntl
import os
import stat
from contextlib import contextmanager
from pathlib import Path

FEEDBACK_DIRNAME = ".ai/feedback"
LEDGER_SUBDIR = "ledger"
QUEUE_SUBDIR = "queue"
TRIAGE_SUBDIR = "triage"
DRAFT_DIRNAME = "tmp/_feedback"
LOCK_FILENAME = ".writer.lock"


class FeedbackPathError(Exception):
    """ガード違反（触ってはならない形のパス）。読み書きは一切行われない。"""


class FeedbackMissing(FeedbackPathError):
    """置き場がまだ**存在しない**（未検出）。CLI は EXIT_NOT_FOUND に落とす。"""


def repo_root() -> Path:
    """このパッケージを含むリポジトリの root。"""
    return Path(__file__).resolve().parents[1]


def _resolved_root(root) -> Path:
    resolved = Path(root).resolve()
    if not resolved.is_dir():
        raise FeedbackPathError(f"repo-root がディレクトリでない: {resolved}")
    return resolved


def resolve_within_repo(path, root) -> Path:
    """``path`` が repo-root 配下の安全なパスかを検査し、正規化済みパスを返す。

    実在チェックは行わない（存在しないパスの「書き先」検査にも使うため）。
    ガード1〜4 のいずれかに掛かれば :class:`FeedbackPathError`（fail-close）。
    """
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


def feedback_dir(root, *, create: bool = False) -> Path:
    """``<repo-root>/.ai/feedback`` を返す（``create`` で不在時に作成）。"""
    target = resolve_within_repo(FEEDBACK_DIRNAME, root)
    if not target.exists():
        if not create:
            raise FeedbackMissing(f"台帳の置き場が無い: {target}")
        target.mkdir(parents=True)
    if not target.is_dir():
        raise FeedbackPathError(f"台帳の置き場がディレクトリでない: {target}")
    return target


def subdir(root, name: str, *, create: bool = False) -> Path:
    """``.ai/feedback/<name>`` を返す（``name`` は固定の3種のみ）。"""
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
    """``.ai/feedback/<name>/<filename>`` を返す（直下・非 symlink を再検査する）。"""
    directory = subdir(root, name, create=create_dir)
    checked = resolve_within_repo(directory / filename, root)
    if checked.parent != directory.resolve():
        raise FeedbackPathError(f"サブディレクトリの直下ではない: {checked}")
    if checked.is_symlink():
        raise FeedbackPathError(f"文書が symlink: {checked}")
    return checked


def draft_path(root, given) -> Path:
    """下書き（``--from``）のパスを検査して返す。**repo-root 配下のみ**許可する。"""
    checked = resolve_within_repo(given, root)
    if checked.is_symlink():
        raise FeedbackPathError(f"下書きが symlink: {checked}")
    if not checked.is_file():
        raise FeedbackMissing(f"下書きが無い: {checked}")
    return checked


def draft_dir(root, *, create: bool = False) -> Path:
    """``tmp/_feedback``（下書き置き場・版管理外）を返す。"""
    target = resolve_within_repo(DRAFT_DIRNAME, root)
    if not target.exists():
        if not create:
            raise FeedbackMissing(f"下書き置き場が無い: {target}")
        target.mkdir(parents=True)
    if not target.is_dir():
        raise FeedbackPathError(f"下書き置き場がディレクトリでない: {target}")
    return target


@contextmanager
def writer_lock(root):
    """CLI の書込みを1つの安定した lock inode で直列化する（``karte/paths.py`` と同型）。"""
    directory = feedback_dir(root, create=True)
    handle = os.open(
        directory / LOCK_FILENAME,
        os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o600,
    )
    try:
        metadata = os.fstat(handle)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise FeedbackPathError("writer lock は単一の通常ファイルでなければならない")
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield
    finally:
        os.close(handle)


def read_text(path: Path) -> str:
    if path.is_symlink():
        raise FeedbackPathError(f"読み込み直前の再検査で symlink を検知: {path}")
    if not path.is_file():
        raise FeedbackPathError(f"通常ファイルではない: {path}")
    return path.read_text(encoding="utf-8")


def write_text_atomic(path: Path, text: str) -> None:
    """同一ディレクトリ内の一時ファイル経由で置き換える（``os.replace`` は原子的）。

    書込直前の symlink 再検査は **best-effort** であって原子的ではない
    （``karte/paths.py::write_text_atomic`` の K-04 と同じ限界・同じ脅威モデル）。
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
