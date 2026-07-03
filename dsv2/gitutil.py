"""``git mv`` の薄いラッパ（reverse の status 遷移・rename の改名で共用）。

v2 では status 遷移（fnd/open → fnd/resolved）も改題も **git rename** で行い、履歴で追跡可能に
する（PR8「消さない」と整合）。git 管理外（テスト等）では通常の filesystem move にフォールバック
して警告を返す。
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def git_mv(root: Path, src_rel: str, dst_rel: str) -> str:
    """``root`` 内で ``src_rel`` → ``dst_rel`` を移動する。返り値 ``"git"`` or ``"fs"``。"""
    dst = root / dst_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["git", "-C", str(root), "mv", src_rel, dst_rel],
        capture_output=True, text=True,
    )
    if proc.returncode == 0:
        return "git"
    # git 管理外 or 未追跡: filesystem move にフォールバック
    os.replace(root / src_rel, dst)
    return "fs"
