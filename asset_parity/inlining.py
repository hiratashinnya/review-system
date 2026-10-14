"""Copilot placement of a `user-invocable: false` skill: inlined into instructions, or not."""

from __future__ import annotations

import re
from pathlib import Path

from .copilot_paths import copilot_instructions_path, inline_slot_path
from .inventory import SKILL, Asset


def principles_marker_pattern(name: str) -> re.Pattern[str]:
    """The whole `principles-source` marker line naming `.ai/skills/<name>/SKILL.md`.

    The comment end and the 64-hex `sha256` field are part of the match, so a truncated or
    malformed line does not count as inlined. The only writer is
    `guidance_sync/sync.py::_principles_marker` (for `spec-principles` alone); the format is
    repeated here rather than imported, and `tests/unit/test_asset_parity_inlining_marker.py`
    pins the two together. Whether the inlined body is current is a separate concern.
    """
    return re.compile(
        rf"<!-- principles-source: \.ai/skills/{re.escape(name)}/SKILL\.md; "
        r"sha256: [0-9a-f]{64} -->"
    )


def is_inlined_into_copilot_instructions(asset: Asset, root: Path) -> bool:
    """True when `.github/copilot-instructions.md` carries the skill's complete marker line."""
    instructions = copilot_instructions_path(root)
    if asset.kind != SKILL or not instructions.is_file():
        return False
    marker = principles_marker_pattern(asset.name)
    lines = instructions.read_text(encoding="utf-8").splitlines()
    return any(marker.fullmatch(line) for line in lines)


def principle_github_paths(asset: Asset, root: Path) -> list[Path]:
    """Copilot place(s) expected for a `user-invocable: false` skill.

    An empty list when it is really inlined (no discrete file). Otherwise only its inline
    slot, which is never a file: `asset-lateral-deploy` routes such a skill to Instructions,
    never to a skill/prompt, so a plain `.github/skills/<name>/SKILL.md` is not accepted
    and the cell is MISSING unless `exceptions.py` registers a documented non-mirror.
    """
    if is_inlined_into_copilot_instructions(asset, root):
        return []
    return [inline_slot_path(asset.name, root)]
