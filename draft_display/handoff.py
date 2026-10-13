"""handoff ファイルの特定・検証・読み出し（SubagentStop フックが使う）。

サブエージェントの最終応答にある ``HANDOFF: tmp/_handoff/gh-create-issue--<key>.md`` 行だけを
信頼の入口とし、名前形状・親ディレクトリ・symlink でないことを検証してから読む。
"""

from __future__ import annotations

import re
from pathlib import Path

AGENT_TYPE = "gh-create-issue"
HANDOFF_DIR_REL = "tmp/_handoff"
MAX_DISPLAY_BYTES = 64 * 1024

_HANDOFF_LINE = re.compile(
    r"HANDOFF:\s*(" + re.escape(HANDOFF_DIR_REL) + r"/gh-create-issue--[A-Za-z0-9][A-Za-z0-9._-]*\.md)"
)


def find_handoff_rel(text: str) -> str | None:
    """テキスト中の最後の ``HANDOFF:`` 行のパス（リポジトリ相対）を返す。無ければ ``None``。"""
    matches = _HANDOFF_LINE.findall(text or "")
    return matches[-1] if matches else None


def resolve_handoff(project_root: Path, rel: str) -> Path | None:
    """``rel`` が ``<root>/tmp/_handoff`` 直下の通常ファイルなら絶対パスを返す。それ以外は ``None``。"""
    handoff_dir = project_root / HANDOFF_DIR_REL
    candidate = project_root / rel
    try:
        if candidate.is_symlink() or not candidate.is_file():
            return None
        if candidate.parent.resolve() != handoff_dir.resolve():
            return None
    except OSError:
        return None
    return candidate


def read_for_display(handoff: Path) -> tuple[str, bool] | None:
    """表示用本文と「切り詰めたか」を返す。読めなければ ``None``。"""
    try:
        with handoff.open("rb") as stream:
            raw = stream.read(MAX_DISPLAY_BYTES + 1)
    except OSError:
        return None
    truncated = len(raw) > MAX_DISPLAY_BYTES
    return raw[:MAX_DISPLAY_BYTES].decode("utf-8", errors="replace"), truncated
