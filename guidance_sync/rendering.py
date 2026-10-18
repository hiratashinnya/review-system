"""生成 bytes と hash marker を組み立てる。"""

from __future__ import annotations

import hashlib
from typing import Callable

from .sources import (
    COMMON_SOURCE,
    PRINCIPLES_MARKER_RE,
    PRINCIPLES_SOURCE,
    TARGETS,
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _body(data: bytes) -> bytes:
    """原稿間の結合を決定的にするため、末尾改行をちょうど1つにする。"""

    return data.rstrip(b"\n") + b"\n"


def _principles_marker(principles: bytes) -> bytes:
    return (
        f"<!-- principles-source: {PRINCIPLES_SOURCE}; "
        f"sha256: {_sha256(principles)} -->"
    ).encode("utf-8")


def _source_dependency_errors(*, load: Callable[[str], bytes]) -> list[str]:
    """共通 guidance の意味保存写しが spec-principles 正本に追従しているか返す。"""

    try:
        common = load(COMMON_SOURCE)
        principles = load(PRINCIPLES_SOURCE)
    except (OSError, RuntimeError) as exc:
        return [f"原稿依存を読めません: {exc}"]
    expected = _sha256(principles)
    match = PRINCIPLES_MARKER_RE.search(common)
    if match is None:
        return [
            f"{COMMON_SOURCE} に {PRINCIPLES_SOURCE} の principles-source marker がありません"
        ]
    recorded = match.group(1).decode("ascii")
    if recorded != expected:
        return [
            f"{COMMON_SOURCE} の principles-source hash が {PRINCIPLES_SOURCE} と一致しません: "
            f"記録 {recorded} / 現在 {expected}"
        ]
    return []


def rendered_bytes(target: str, *, load: Callable[[str], bytes]) -> bytes:
    """``target`` の完全な生成結果を返す。I/O は ``load`` へ分離する。"""

    try:
        platform_source = TARGETS[target]
    except KeyError as exc:  # pragma: no cover - 呼び出し側のプログラミングエラー
        raise ValueError(f"生成対象ではありません: {target}") from exc
    common = load(COMMON_SOURCE)
    principles = load(PRINCIPLES_SOURCE)
    platform = load(platform_source)
    marker = (
        "<!-- generated-by: python3 -m guidance_sync render; edit-source-only -->\n"
        f"<!-- common-source: {COMMON_SOURCE}; sha256: {_sha256(common)} -->\n"
        f"{_principles_marker(principles).decode('utf-8')}\n"
        f"<!-- platform-source: {platform_source}; sha256: {_sha256(platform)} -->\n\n"
    ).encode("utf-8")
    return marker + _body(common) + b"\n" + _body(platform)
