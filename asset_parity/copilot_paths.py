"""Every Copilot (`.github/`) path `asset_parity` looks up, defined once.

Covers the plain skill, the orchestrator prompt, the agent file, the instructions file, the
inline slot of a principle skill and the mirror roots scanned for orphans. The Codex trees
(`.codex/agents/`, `.agents/skills/`) are not Copilot paths and stay in `trees.py`.
"""

from __future__ import annotations

from pathlib import Path

from .inventory import AGENT


def _skills_dir(root: Path) -> Path:
    return root / ".github" / "skills"


def _prompts_dir(root: Path) -> Path:
    return root / ".github" / "prompts"


def _agents_dir(root: Path) -> Path:
    return root / ".github" / "agents"


def copilot_skill_path(name: str, root: Path) -> Path:
    """Plain Copilot skill `.github/skills/<name>/SKILL.md`."""
    return _skills_dir(root) / name / "SKILL.md"


def copilot_prompt_path(name: str, root: Path) -> Path:
    """Copilot prompt `.github/prompts/<name>.prompt.md` (an orchestrator skill's mirror)."""
    return _prompts_dir(root) / f"{name}.prompt.md"


def copilot_agent_path(name: str, root: Path) -> Path:
    """Copilot agent `.github/agents/<name>.agent.md`."""
    return _agents_dir(root) / f"{name}.agent.md"


def copilot_instructions_path(root: Path) -> Path:
    """Always-loaded Copilot instructions `.github/copilot-instructions.md`."""
    return root / ".github" / "copilot-instructions.md"


def copilot_mirror_roots(kind: str, root: Path) -> list[Path]:
    """Copilot directories scanned for mirror assets of `kind` (orphan detection)."""
    if kind == AGENT:
        return [_agents_dir(root)]
    return [_skills_dir(root), _prompts_dir(root)]


class InlineSlotPath(type(Path())):
    """A place that exists only as text inside another file, so it is never a file itself.

    A plain `Path` would answer from the file system, and a file (or a directory with a child)
    that happens to sit at that path would then count as the mirror. This one answers no.
    """

    def is_file(self, *, follow_symlinks: bool = True) -> bool:
        return False


def inline_slot_path(name: str, root: Path) -> Path:
    """Virtual place of a principle skill's inlined text: a marker inside the instructions file.

    That text is not a file of its own, so the path is an `InlineSlotPath` (named under the
    instructions file for display only). A cell that expects it is therefore MISSING until the
    marker exists (or an exemption is registered); neither a plain
    `.github/skills/<name>/SKILL.md` nor anything on disk at the slot can stand in for it.
    """
    return InlineSlotPath(copilot_instructions_path(root), f"principles-source-{name}")
