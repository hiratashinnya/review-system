"""Whether a `user-invocable: false` skill is really inlined into Copilot instructions."""

from __future__ import annotations

from pathlib import Path

from .inventory import SKILL, Asset


def is_inlined_into_copilot_instructions(asset: Asset, root: Path) -> bool:
    """Evidence is the `principles-source: .ai/skills/<name>/SKILL.md` marker that
    `guidance_sync` renders next to each principle inlined into
    `.github/copilot-instructions.md`.
    """
    instructions = root / ".github" / "copilot-instructions.md"
    if asset.kind != SKILL or not instructions.is_file():
        return False
    marker = f"principles-source: .ai/skills/{asset.name}/SKILL.md"
    return marker in instructions.read_text(encoding="utf-8")
