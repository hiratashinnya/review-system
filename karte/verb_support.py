"""verb 実装が共有する部品（fail-close 境界・repo-root・Issue 解決・台帳の読み込み）。"""

import functools
import sys
from pathlib import Path

from . import model, paths
from .active_pointer import read_active
from .errors import KarteNotFound, KarteUsageError
from .exit_codes import EXIT_ERROR, EXIT_NOT_FOUND

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent


def fail_close(func, extra_errors=()):
    """``cmd_*`` を「例外を投げず終了コードを返す」境界にする。

    verb 単位が終了コードの境界（＝呼び出し側は ``main`` 経由でも直呼びでも同じ
    fail-close 挙動を得る）。``main`` にだけ ``try/except`` を置くと、フックやテストのように
    ``cmd_*`` を直接呼ぶ経路では例外が素通りし、拒否されたのに終了コードが返らない。
    """
    refusals = (KarteUsageError, paths.KartePathError, model.KarteFormatError, OSError, *extra_errors)

    @functools.wraps(func)
    def wrapper(args) -> int:
        try:
            return func(args)
        except KarteNotFound as exc:
            print(f"未検出: {exc}", file=sys.stderr)
            return EXIT_NOT_FOUND
        except refusals as exc:
            print(f"拒否（fail-close）: {exc}", file=sys.stderr)
            return EXIT_ERROR

    return wrapper


def repo_root_of(args, default=None, package_root=None) -> Path:
    """台帳の repo-root。``args.repo_root``（テスト専用の上書き）、``default``、main worktree の順。

    ``package_root``＝``karte`` パッケージが動いている worktree（既定はこのファイルの親）。
    """
    override = getattr(args, "repo_root", None)
    if override:
        return Path(override).resolve()
    if default is not None:
        return Path(default)
    return paths.main_worktree_root(package_root or _PACKAGE_ROOT)


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
