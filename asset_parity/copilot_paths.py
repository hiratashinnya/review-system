"""Path definitions for the Copilot (`.github/`) mirror files that `asset_parity` looks up."""

from __future__ import annotations

from pathlib import Path


def copilot_skill_path(name: str, root: Path) -> Path:
    """Single definition of the plain Copilot skill path `.github/skills/<name>/SKILL.md`."""
    return root / ".github" / "skills" / name / "SKILL.md"


def copilot_instructions_path(root: Path) -> Path:
    """Single definition of the always-loaded Copilot instructions `.github/copilot-instructions.md`."""
    return root / ".github" / "copilot-instructions.md"


def inline_slot_path(name: str, root: Path) -> Path:
    """Virtual place of a principle skill's inlined text: a marker inside the instructions file.

    That text is not a file of its own, so this path lies *under* the instructions file and
    `is_file()` is never true for it. A cell that expects it is therefore MISSING until the
    marker exists (or an exemption is registered); a plain `.github/skills/<name>/SKILL.md`
    cannot stand in for it.
    """
    return copilot_instructions_path(root) / f"principles-source:{name}"
