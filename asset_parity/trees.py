"""Per-tree mirror path conventions for the three parity target trees.

Verified against the actual repo layout (not assumed) as part of the issue #155 audit:

  * GitHub Copilot  — skill: `.github/skills/<name>/SKILL.md`
                      agent: `.github/agents/<name>.agent.md` (defined in `copilot_paths.py`)
  * Codex CLI agent — agent: `.codex/agents/<name>.toml`  (no skill-shaped tree)
  * Codex CLI skill — skill: `.agents/skills/<name>/SKILL.md`  (top-level `.agents/`,
                      NOT nested under `.codex/` — this is Codex's documented
                      repo-scoped skill discovery path)  (no agent-shaped tree)

Two *structural* (not per-asset-exception) rules come out of `.claude/skills/
asset-lateral-deploy/SKILL.md`'s routing decision tree: a parity-seed skill's
`disable-model-invocation`/`user-invocable` frontmatter changes which Copilot file is expected:

  * `disable-model-invocation: true` (orchestrator, e.g. `/spec-pipeline`) → Copilot
    represents it as a **Prompt** (`.github/prompts/<name>.prompt.md`), not a Skill.
  * `user-invocable: false` (always-loaded principle, e.g. `spec-principles`) → Copilot
    inlines it into `.github/copilot-instructions.md` (no discrete file) only if it really
    is, as read from that file's content (`inlining.py`); else a plain skill file is not accepted.

Codex's `.agents/skills/` tree does not have this split (verified: orchestrator-mode
skills like `asset-pipeline`/`spec-pipeline` and even the `user-invocable: false`
`spec-principles` are all plain `SKILL.md` files there), so no special-casing is needed
for that tree.
"""

from __future__ import annotations

from pathlib import Path

from . import copilot_paths
from .inlining import principle_github_paths
from .inventory import AGENT, MODE_ORCHESTRATOR, MODE_PRINCIPLE, SKILL, Asset

GITHUB = "github"
CODEX = "codex"
AGENTS_DIR = "agents_dir"  # `.agents/skills/` (Codex CLI skill discovery path)

ALL_TREES: tuple[str, ...] = (GITHUB, CODEX, AGENTS_DIR)

TREE_LABELS: dict[str, str] = {
    GITHUB: ".github (Copilot)",
    CODEX: ".codex/agents (Codex CLI agent)",
    AGENTS_DIR: ".agents/skills (Codex CLI skill)",
}


def applicable_trees(kind: str) -> tuple[str, ...]:
    """Which trees can structurally hold this asset kind (basis for N/A cells)."""
    if kind == SKILL:
        return (GITHUB, AGENTS_DIR)
    if kind == AGENT:
        return (GITHUB, CODEX)
    raise ValueError(f"unknown asset kind: {kind!r}")


def expected_paths(asset: Asset, tree: str, root: Path) -> list[Path]:
    """Candidate path(s) where `asset` would be expected to live in `tree`.

    Empty means no discrete file is expected (exempt/N/A, not a missing mirror). That follows
    from (kind, tree, mode) alone, except for a `user-invocable: false` skill on GITHUB, which
    reads `.github/copilot-instructions.md` (file I/O) to see if it is really inlined. When
    several paths are returned, presence of any one counts as present.
    """
    if tree not in applicable_trees(asset.kind):
        return []

    if asset.kind == AGENT:
        if tree == GITHUB:
            return [copilot_paths.copilot_agent_path(asset.name, root)]
        if tree == CODEX:
            return [root / ".codex" / "agents" / f"{asset.name}.toml"]
        return []

    # asset.kind == SKILL
    if tree == AGENTS_DIR:
        return [root / ".agents" / "skills" / asset.name / "SKILL.md"]
    if tree == GITHUB:
        if asset.mode == MODE_PRINCIPLE:
            return principle_github_paths(asset, root)  # [] when inlined (no discrete file)
        if asset.mode == MODE_ORCHESTRATOR:
            return [copilot_paths.copilot_prompt_path(asset.name, root)]
        return [copilot_paths.copilot_skill_path(asset.name, root)]
    return []


def mirror_root_dirs(tree: str, kind: str, root: Path) -> list[Path]:
    """Directory (or directories) to scan for "extra" assets not in the parity seed.

    Used for the orphans-in-mirror informational report (assets that exist in a mirror
    but have no `.claude/` parity-seed counterpart at all — the reverse-direction gap).
    """
    if tree not in applicable_trees(kind):
        return []
    if tree == GITHUB:
        return copilot_paths.copilot_mirror_roots(kind, root)
    if kind == AGENT:
        return [root / ".codex" / "agents"]
    return [root / ".agents" / "skills"]
