"""Parity seed inventory: enumerates active Claude asset wrappers.

The parity matrix starts from the two loader-facing Claude roots:
``.claude/skills/*/SKILL.md`` and ``.claude/agents/*.md``.  Shared, inactive
material under ``.ai/`` is deliberately outside this inventory.  The common
normative Source of Truth remains under ``.ai/skills`` and ``.ai/agents``;
Claude wrappers are only the comparison seeds used to enumerate parity rows.

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

# Common normative content is edited here.  These directories are not scanned
# as parity seeds because they are platform-neutral source text, not PF wrappers.
COMMON_SOT_SKILLS_DIR = ".ai/skills"
COMMON_SOT_AGENTS_DIR = ".ai/agents"

# The parity matrix is about loader-facing wrappers, not every Markdown file in
# ``.claude/``.  Claude is the matrix's discovery seed; being a seed does not
# make it the common normative Source of Truth.
PARITY_SEED_SKILLS_DIR = ".claude/skills"
PARITY_SEED_AGENTS_DIR = ".claude/agents"
NON_NORMATIVE_SHARED_DIRS: tuple[str, ...] = (
    ".ai/rationale",
    ".ai/troubleshooting",
    ".ai/schema",
    ".ai/guidance",
)

# Invocation modes — meaningful for SKILL kind only (None for AGENT).
MODE_SKILL = "skill"                # default: a model-invocable capability
MODE_ORCHESTRATOR = "orchestrator"  # `disable-model-invocation: true` — user-invoked pipeline
MODE_PRINCIPLE = "principle"        # `user-invocable: false` — always-loaded doctrine

_UNSET = object()


@dataclasses.dataclass(frozen=True, init=False)
class Asset:
    name: str
    kind: str  # SKILL | AGENT
    mode: str | None
    parity_seed_path: Path

    def __init__(
        self,
        name: str,
        kind: str,
        mode: str | None,
        parity_seed_path: Path | object = _UNSET,
        *,
        canonical_path: Path | object = _UNSET,
    ) -> None:
        """Accept the v2 name and the deprecated constructor keyword.

        Supplying both names is allowed only when their values agree.
        """
        if parity_seed_path is _UNSET and canonical_path is _UNSET:
            raise TypeError("missing required argument: parity_seed_path")
        if (
            parity_seed_path is not _UNSET
            and canonical_path is not _UNSET
            and parity_seed_path != canonical_path
        ):
            raise TypeError("parity_seed_path and canonical_path disagree")
        resolved_path = canonical_path if parity_seed_path is _UNSET else parity_seed_path
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "parity_seed_path", resolved_path)

    @property
    def canonical_path(self) -> Path:
        """Deprecated alias for ``parity_seed_path``; retained for compatibility."""
        return self.parity_seed_path


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


def is_parity_seed_path(path: Path | str, root: Path) -> bool:
    """Return whether ``path`` is in one of the two parity seed roots.

    This is intentionally a path-boundary helper rather than a recursive
    ``.claude`` check.  Rationale/troubleshooting/schema files are repository
    records and must never be promoted to parity assets merely because they
    happen to be Markdown files.
    """

    try:
        path_obj = Path(path)
        candidate = path_obj if path_obj.is_absolute() else root / path_obj
        relative = candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    parts = relative.parts
    if len(parts) < 3:
        return False
    if parts[:2] == tuple(PARITY_SEED_SKILLS_DIR.split("/")):
        return parts[-1] == "SKILL.md" and len(parts) == 4
    if parts[:2] == tuple(PARITY_SEED_AGENTS_DIR.split("/")):
        return parts[-1].endswith(".md") and len(parts) == 3
    return False


def scan_canonical(root: Path) -> list[Asset]:
    """Deprecated compatibility alias for :func:`scan_parity_seeds`."""
    return scan_parity_seeds(root)


def is_canonical_asset_path(path: Path | str, root: Path) -> bool:
    """Deprecated compatibility alias for :func:`is_parity_seed_path`."""
    return is_parity_seed_path(path, root)
