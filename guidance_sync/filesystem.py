"""working tree を読み書きして生成物を同期・検査する。"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from .rendering import _source_dependency_errors, rendered_bytes
from .sources import REPO_ROOT, TARGETS


def _filesystem_loader(root: Path) -> Callable[[str], bytes]:
    return lambda relative: (root / relative).read_bytes()


def render(root: Path = REPO_ROOT) -> list[str]:
    """生成物を明示的に更新し、変更した相対パスを返す。"""

    load = _filesystem_loader(root)
    changed: list[str] = []
    for target in TARGETS:
        expected = rendered_bytes(target, load=load)
        path = root / target
        current = path.read_bytes() if path.is_file() else None
        if current != expected:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(expected)
            changed.append(target)
    return changed


def check(root: Path = REPO_ROOT) -> list[str]:
    """working tree の生成物 drift を返す。空なら整合している。"""

    load = _filesystem_loader(root)
    errors = _source_dependency_errors(load=load)
    for target in TARGETS:
        path = root / target
        if not path.is_file():
            errors.append(f"生成物がありません: {target}")
            continue
        if path.read_bytes() != rendered_bytes(target, load=load):
            errors.append(
                f"生成物が原稿と一致しません: {target} "
                "（python3 -m guidance_sync render を実行してください）"
            )
    return errors
