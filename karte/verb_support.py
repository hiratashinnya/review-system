"""verb 実装が共有する部品（fail-close 境界・repo-root・Issue 解決・台帳の読み込み）。"""

import functools
import sys
from pathlib import Path

from . import model, paths
from .active_pointer import read_active
from .errors import KarteNotFound, KarteUsageError
from .exit_codes import EXIT_ERROR, EXIT_NOT_FOUND

# `karte` パッケージが置かれているディレクトリ（＝呼び出し元 worktree root の候補）。
# 台帳解決（`repo_root_of`）は main worktree へ変換するが、diff 計算（`invoking_worktree`）は
# 変換前のこの値をそのまま使う——両者を同じ変換に流用しない（Issue #437）。
_PACKAGE_ROOT = Path(__file__).resolve().parent.parent

# repo-root のオーバーライド点（テスト専用）。**既定は None（＝未解決）**で、導出は
# `repo_root_of` が呼ばれたときに行う（K-12 の遅延評価）。全 verb がこの 1 箇所を通る。
_REPO_ROOT = None


def fail_close(func, extra_errors=(), locked=False):
    """``cmd_*`` を「例外を投げず終了コードを返す」境界にする。

    verb 単位が終了コードの境界（＝呼び出し側は ``main`` 経由でも直呼びでも同じ fail-close
    挙動を得る）。``locked=True`` は台帳の書き換え全体を共有 writer lock の中で行う。
    """
    refusals = (KarteUsageError, paths.KartePathError, model.KarteFormatError, OSError, *extra_errors)

    @functools.wraps(func)
    def wrapper(args) -> int:
        try:
            if locked:
                with paths.writer_lock(repo_root_of(args)):
                    return func(args)
            return func(args)
        except KarteNotFound as exc:
            print(f"未検出: {exc}", file=sys.stderr)
            return EXIT_NOT_FOUND
        except refusals as exc:
            print(f"拒否（fail-close）: {exc}", file=sys.stderr)
            return EXIT_ERROR

    return wrapper


def repo_root_of(args) -> Path:
    """台帳の repo-root。``args.repo_root``（テスト専用の上書き）、``_REPO_ROOT``、main worktree の順。"""
    override = getattr(args, "repo_root", None)
    if override:
        return Path(override).resolve()
    if _REPO_ROOT is not None:
        return Path(_REPO_ROOT)
    return paths.main_worktree_root(_PACKAGE_ROOT)


def invoking_worktree() -> Path:
    """``karte`` が今動いている worktree のルート（``git diff`` の cwd 用。main へは収束させない）。"""
    return paths.invoking_worktree_root(_PACKAGE_ROOT)


def parse_int(value, label: str, minimum: int = 1) -> int:
    """``minimum`` 以上の整数に直す。ASCII 数字だけを受け、それ以外は :class:`KarteUsageError`。

    ``str.isdigit()`` だけでは ``"²"`` のような非 ASCII 数字を通し、``int()`` が ``ValueError`` で
    終了コード契約の外へ漏れる。
    """
    text = str(value)
    try:
        number = int(text) if text.isascii() and text.isdigit() else -1
    except ValueError:  # 桁数が多すぎる（int の変換上限）
        number = -1
    if number < minimum:
        raise KarteUsageError(f"{label} は {minimum} 以上の整数: {text[:40]!r}")
    return number


def resolve_issue(args, repo_root, hint="") -> int:
    """``--issue`` が無ければ進行ポインタの ``issue``。ポインタが無い・壊れている・欠けるなら拒否する。"""
    if getattr(args, "issue", None) is not None:
        return paths.validate_issue(args.issue)
    active = read_active(repo_root, required=True)
    if "issue" not in active:
        raise KarteUsageError(
            f"--issue が未指定で、進行ポインタ tmp/_karte/active.json に 'issue' が無い{hint}"
        )
    return paths.validate_issue(active["issue"])


def load_karte(repo_root, issue: int, hint=""):
    """``(path, Karte)``。置き場・台帳が無ければ :class:`KarteNotFound`（未検出＝ガード違反ではない）。"""
    try:
        path = paths.karte_path(issue, repo_root)
    except paths.KarteMissing as exc:
        raise KarteNotFound(f"{exc}{hint}") from None
    if not path.is_file():
        raise KarteNotFound(f"カルテが無い: {path}{hint}")
    return path, model.parse(paths.read_text(path))
