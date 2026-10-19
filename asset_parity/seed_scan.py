"""Enumerate active Claude parity seeds."""

from pathlib import Path

from .asset import Asset
from .frontmatter import read_frontmatter
from .seed_paths import (AGENT, SKILL, MODE_SKILL, MODE_ORCHESTRATOR, MODE_PRINCIPLE,
                         PARITY_SEED_SKILLS_DIR, PARITY_SEED_AGENTS_DIR)


def scan_parity_seeds(root: Path) -> list[Asset]:
    """Enumerate parity seeds under `.claude/skills/` and `.claude/agents/`.

    Files with no parseable frontmatter (no leading/closing ``---`` block) are skipped
    silently — those are shared reference docs (e.g. `doc-system-v2-authoring.md`), not
    independently-identified subagent/skill definitions with a name of their own.
    """
    assets: list[Asset] = []

    skills_dir = root / PARITY_SEED_SKILLS_DIR
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        fm = read_frontmatter(skill_md.read_text(encoding="utf-8"))
        if fm is None:
            continue
        mode = MODE_SKILL
        if str(fm.get("disable-model-invocation", "")).strip().lower() == "true":
            mode = MODE_ORCHESTRATOR
        elif str(fm.get("user-invocable", "")).strip().lower() == "false":
            mode = MODE_PRINCIPLE
        assets.append(Asset(name=skill_md.parent.name, kind=SKILL, mode=mode,
                            parity_seed_path=skill_md))

    agents_dir = root / PARITY_SEED_AGENTS_DIR
    for agent_md in sorted(agents_dir.glob("*.md")):
        fm = read_frontmatter(agent_md.read_text(encoding="utf-8"))
        if fm is None:
            continue
        assets.append(Asset(name=agent_md.stem, kind=AGENT, mode=None,
                            parity_seed_path=agent_md))

    return assets


