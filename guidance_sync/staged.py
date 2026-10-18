"""staged index の guidance 原稿と生成物を検査する。"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

from .git_index import _index_loader, _staged_paths
from .rendering import _source_dependency_errors, rendered_bytes
from .sources import COMMON_SOURCE, PRINCIPLES_SOURCE, REPO_ROOT, TARGETS


def staged_check(
    root: Path = REPO_ROOT,
    *,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> list[str]:
    """staged index 内の原稿と生成物だけを比較する。

    原稿が stage された場合は依存する生成物も stage 済みであることを要求する。
    生成物だけが stage された場合も index 上の原稿との一致を検査する。
    """

    try:
        staged = _staged_paths(root, runner=runner)
    except RuntimeError as exc:
        return [str(exc)]
    required_targets: set[str] = set()
    require_common = PRINCIPLES_SOURCE in staged
    if COMMON_SOURCE in staged or require_common:
        required_targets.update(TARGETS)
    for target, platform_source in TARGETS.items():
        if platform_source in staged or target in staged:
            required_targets.add(target)
    if not required_targets:
        return []

    errors: list[str] = []
    load = _index_loader(root, runner=runner)
    if require_common and COMMON_SOURCE not in staged:
        errors.append(
            f"{PRINCIPLES_SOURCE} の変更に対応する意味保存写しが stage されていません: "
            f"{COMMON_SOURCE}"
        )
    errors.extend(_source_dependency_errors(load=load))
    for target in sorted(required_targets):
        if target not in staged:
            errors.append(f"原稿の変更に対応する生成物が stage されていません: {target}")
            continue
        try:
            actual = load(target)
            expected = rendered_bytes(target, load=load)
        except RuntimeError as exc:
            errors.append(str(exc))
            continue
        if actual != expected:
            errors.append(
                f"staged index の生成物が staged 原稿と一致しません: {target} "
                "（render 後に生成物を明示的に stage してください）"
            )
    return errors
