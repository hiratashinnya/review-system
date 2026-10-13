"""Copilot placement of a skill: really inlined into instructions, or its plain skill path."""

from __future__ import annotations

from pathlib import Path

from .inventory import SKILL, Asset


def principles_marker_prefix(name: str) -> str:
    """Start of the `principles-source` marker naming `.ai/skills/<name>/SKILL.md`.

    The only writer is `guidance_sync/sync.py::_principles_marker`, and it renders this
    marker for `spec-principles` alone. The format is repeated here rather than imported,
    and `tests/unit/test_asset_parity_inlining_marker.py` pins the two together.
    """
    return f"<!-- principles-source: .ai/skills/{name}/SKILL.md;"


def is_inlined_into_copilot_instructions(asset: Asset, root: Path) -> bool:
    """True when `.github/copilot-instructions.md` carries the skill's marker line."""
    instructions = root / ".github" / "copilot-instructions.md"
    if asset.kind != SKILL or not instructions.is_file():
        return False
    marker = principles_marker_prefix(asset.name)
    lines = instructions.read_text(encoding="utf-8").splitlines()
    return any(line.startswith(marker) for line in lines)


def copilot_skill_path(name: str, root: Path) -> Path:
    """Single definition of the plain Copilot skill path `.github/skills/<name>/SKILL.md`."""
    return root / ".github" / "skills" / name / "SKILL.md"


def principle_github_paths(asset: Asset, root: Path) -> list[Path]:
    """Copilot file(s) expected for a `user-invocable: false` skill.

    An empty list when it is really inlined (no discrete file); otherwise the plain skill
    path, so a missing mirror needs an `exceptions.py` entry and is reported MISSING without one.
    """
    if is_inlined_into_copilot_instructions(asset, root):
        return []
    return [copilot_skill_path(asset.name, root)]
