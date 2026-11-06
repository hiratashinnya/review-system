"""verb の終了コード境界（fail-close）と、台帳ロック要否の宣言。

設計理由は [.ai/rationale/karte-module-split.md](../.ai/rationale/karte-module-split.md)。
"""

import argparse
import functools
import sys
from typing import Callable, Protocol, cast

from . import model, paths
from .errors import KarteNotFound, KarteUsageError
from .exit_codes import EXIT_ERROR, EXIT_NOT_FOUND
from .touched import TouchedError
from .repo_roots import repo_root_of

_REFUSALS = (KarteUsageError, paths.KartePathError, model.KarteFormatError, OSError, TouchedError)


class Verb(Protocol):
    """:func:`fail_close` が返す ``cmd(args) -> 終了コード``。ロック要否の宣言を ``locked`` に持つ。"""

    __name__: str
    locked: bool

    def __call__(self, args: argparse.Namespace) -> int: ...


def fail_close(
    *, locked: bool, prepare: Callable[..., object] | None = None
) -> Callable[[Callable[..., int]], Verb]:
    """``func(args, repo_root)`` を、終了コードを返す ``cmd(args)`` にするデコレータ。

    ``locked`` は必須で既定値を持たない（True: 共有 writer lock の中で実行、False: ロックなし）。
    宣言は返す関数の ``locked`` 属性に残り、:func:`require_declared` が登録時に検査する。
    repo-root はここで 1 回だけ解決して ``func`` へ渡す（verb 内で再解決しない）。

    ``prepare(args, repo_root)`` を渡すと、ロックを取る**前**に 1 回だけ呼び、その戻り値を
    ``func(args, repo_root, prepared)`` の第 3 引数に渡す。標準入力など閉じない可能性のある
    入力の読み取りをロックの外に置く段で、その段での拒否はロック前に起きる（何も作らない）。
    """
    if not isinstance(locked, bool):
        raise TypeError(f"locked は True/False で明示する: {locked!r}")

    def decorate(func: Callable[..., int]) -> Verb:
        @functools.wraps(func)
        def wrapper(args: argparse.Namespace) -> int:
            try:
                repo_root = repo_root_of(args)
                extra = () if prepare is None else (prepare(args, repo_root),)
                if locked:
                    with paths.writer_lock(repo_root):
                        return func(args, repo_root, *extra)
                return func(args, repo_root, *extra)
            except KarteNotFound as exc:
                print(f"未検出: {exc}", file=sys.stderr)
                return EXIT_NOT_FOUND
            except _REFUSALS as exc:
                print(f"拒否（fail-close）: {exc}", file=sys.stderr)
                return EXIT_ERROR

        verb = cast(Verb, wrapper)
        verb.locked = locked
        return verb

    return decorate


def require_declared(subparsers) -> None:
    """全 verb が :func:`fail_close` でロック要否を宣言済みでなければ登録を拒否する。"""
    for name, parser in subparsers.choices.items():
        if not isinstance(getattr(parser.get_default("func"), "locked", None), bool):
            raise ValueError(
                f"verb {name!r} はロック要否を宣言していない"
                "（verb_boundary.fail_close(locked=True/False) で包む）"
            )
