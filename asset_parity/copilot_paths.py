"""Path definitions for the Copilot (`.github/`) mirror files that `asset_parity` looks up."""

from __future__ import annotations

from pathlib import Path


def copilot_skill_path(name: str, root: Path) -> Path:
    """Single definition of the plain Copilot skill path `.github/skills/<name>/SKILL.md`."""
    return root / ".github" / "skills" / name / "SKILL.md"
