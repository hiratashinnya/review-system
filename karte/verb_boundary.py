"""verb の終了コード境界（fail-close）と、台帳ロック要否の宣言。

設計理由は [.ai/rationale/karte-module-split.md](../.ai/rationale/karte-module-split.md)。
"""

import functools
import sys

from . import model, paths
from .errors import KarteNotFound, KarteUsageError
from .exit_codes import EXIT_ERROR, EXIT_NOT_FOUND
from .touched import TouchedError
from .verb_support import repo_root_of

_REFUSALS = (KarteUsageError, paths.KartePathError, model.KarteFormatError, OSError, TouchedError)


def fail_close(*, locked):
    """``func(args, repo_root)`` を、終了コードを返す ``cmd(args)`` にするデコレータ。

    ``locked`` は必須で既定値を持たない（True: 共有 writer lock の中で実行、False: ロックなし）。
    宣言は返す関数の ``locked`` 属性に残り、:func:`require_declared` が登録時に検査する。
    repo-root はここで 1 回だけ解決して ``func`` へ渡す（verb 内で再解決しない）。
    """
    if not isinstance(locked, bool):
        raise TypeError(f"locked は True/False で明示する: {locked!r}")

    def decorate(func):
        @functools.wraps(func)
        def wrapper(args) -> int:
            try:
                repo_root = repo_root_of(args)
                if locked:
                    with paths.writer_lock(repo_root):
                        return func(args, repo_root)
                return func(args, repo_root)
            except KarteNotFound as exc:
                print(f"未検出: {exc}", file=sys.stderr)
                return EXIT_NOT_FOUND
            except _REFUSALS as exc:
                print(f"拒否（fail-close）: {exc}", file=sys.stderr)
                return EXIT_ERROR

        wrapper.locked = locked
        return wrapper

    return decorate


def require_declared(subparsers) -> None:
    """全 verb が :func:`fail_close` でロック要否を宣言済みでなければ登録を拒否する。"""
    for name, parser in subparsers.choices.items():
        if not isinstance(getattr(parser.get_default("func"), "locked", None), bool):
            raise ValueError(
                f"verb {name!r} はロック要否を宣言していない"
                "（verb_boundary.fail_close(locked=True/False) で包む）"
            )
