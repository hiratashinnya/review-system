"""Per-tree mirror path conventions for the three non-canonical asset trees.

Verified against the actual repo layout (not assumed) as part of the issue #155 audit:

  * GitHub Copilot  — skill: `.github/skills/<name>/SKILL.md`
                      agent: `.github/agents/<name>.agent.md`
  * Codex CLI agent — agent: `.codex/agents/<name>.toml`  (no skill-shaped tree)
  * Codex CLI skill — skill: `.agents/skills/<name>/SKILL.md`  (top-level `.agents/`,
                      NOT nested under `.codex/` — this is Codex's documented
                      repo-scoped skill discovery path)  (no agent-shaped tree)

One additional, *structural* (not per-asset-exception) rule comes straight out of
`.claude/skills/asset-lateral-deploy/SKILL.md`'s routing decision tree: a canonical
skill's `disable-model-invocation`/`user-invocable` frontmatter changes *which* Copilot
file form is expected, not whether one is:

  * `disable-model-invocation: true` (orchestrator, e.g. `/spec-pipeline`) → Copilot
    represents it as a **Prompt** (`.github/prompts/<name>.prompt.md`), not a Skill.
  * `user-invocable: false` (always-loaded principle, e.g. `spec-principles`) → Copilot
    inlines it into `.github/copilot-instructions.md`; there is no discrete per-asset
    file at all, so this is reported as a structural N/A, not a MISSING.

Codex's `.agents/skills/` tree does not have this split (verified: orchestrator-mode
skills like `asset-pipeline`/`spec-pipeline` and even the `user-invocable: false`
`spec-principles` are all plain `SKILL.md` files there), so no special-casing is needed
for that tree.
"""

from __future__ import annotations

from pathlib import Path

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

    Returns an empty list when the (kind, tree, mode) combination is structurally not
    expected to produce a discrete file at all — callers should treat that as N/A, not
    as a missing mirror. When more than one path is returned, presence of *any* one of
    them counts as present (OR — currently only the Copilot skill-vs-prompt case).
    """
    if tree not in applicable_trees(asset.kind):
        return []

    if asset.kind == AGENT:
        if tree == GITHUB:
            return [root / ".github" / "agents" / f"{asset.name}.agent.md"]
        if tree == CODEX:
            return [root / ".codex" / "agents" / f"{asset.name}.toml"]
        return []

    # asset.kind == SKILL
    if tree == AGENTS_DIR:
        return [root / ".agents" / "skills" / asset.name / "SKILL.md"]
    if tree == GITHUB:
        if asset.mode == MODE_PRINCIPLE:
            return []  # inlined into copilot-instructions.md — no discrete file expected
        if asset.mode == MODE_ORCHESTRATOR:
            return [root / ".github" / "prompts" / f"{asset.name}.prompt.md"]
        return [root / ".github" / "skills" / asset.name / "SKILL.md"]
    return []


def mirror_root_dirs(tree: str, kind: str, root: Path) -> list[Path]:
    """Directory (or directories) to scan for "extra" assets not in the canonical tree.

    Used for the orphans-in-mirror informational report (assets that exist in a mirror
    but have no canonical `.claude/` counterpart at all — the reverse-direction gap).
    """
    if tree not in applicable_trees(kind):
        return []
    if kind == AGENT:
        return [root / ".github" / "agents"] if tree == GITHUB else [root / ".codex" / "agents"]
    if tree == GITHUB:
        return [root / ".github" / "skills", root / ".github" / "prompts"]
    return [root / ".agents" / "skills"]
