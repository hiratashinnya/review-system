"""Canonical asset inventory: enumerates `.claude/skills/*/SKILL.md` and `.claude/agents/*.md`.

依存仕様（out-of-graph・版なし・補助ナビ）:
  * `.claude/skills/asset-lateral-deploy/SKILL.md`（振り分け決定木＝`disable-model-invocation`/
    `user-invocable` フロントマターで skill/prompt/agent/instructions を分類する根拠）
  * `.claude/tailoring-registry.md`（意図的な非移植の記録）
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from .frontmatter import read_frontmatter

SKILL = "skill"
AGENT = "agent"

# Invocation modes — meaningful for SKILL kind only (None for AGENT).
MODE_SKILL = "skill"                # default: a model-invocable capability
MODE_ORCHESTRATOR = "orchestrator"  # `disable-model-invocation: true` — user-invoked pipeline
MODE_PRINCIPLE = "principle"        # `user-invocable: false` — always-loaded doctrine


@dataclasses.dataclass(frozen=True)
class Asset:
    name: str
    kind: str  # SKILL | AGENT
    mode: str | None
    canonical_path: Path


def scan_canonical(root: Path) -> list[Asset]:
    """Enumerate canonical assets under `.claude/skills/` and `.claude/agents/`.

    Files with no parseable frontmatter (no leading/closing ``---`` block) are skipped
    silently — those are shared reference docs (e.g. `doc-system-v2-authoring.md`), not
    independently-identified subagent/skill definitions with a name of their own.
    """
    assets: list[Asset] = []

    skills_dir = root / ".claude" / "skills"
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
                            canonical_path=skill_md))

    agents_dir = root / ".claude" / "agents"
    for agent_md in sorted(agents_dir.glob("*.md")):
        fm = read_frontmatter(agent_md.read_text(encoding="utf-8"))
        if fm is None:
            continue
        assets.append(Asset(name=agent_md.stem, kind=AGENT, mode=None,
                             canonical_path=agent_md))

    return assets
