"""Documented intentional non-mirrors — assets that legitimately have no counterpart
in a given tree, so a missing mirror there should be reported as EXEMPT, not MISSING.

This list must mirror decisions **already recorded elsewhere**, not invent new ones
(per the issue #155 task brief: "check how the repo already documents such decisions
... before inventing a new mechanism"). The source of truth is
`.claude/tailoring-registry.md`'s trailing bullet notes, as of this tool's writing:

  * `agy-delegate`（スキル＋エージェント）: agy MCP はローカル CLI／Windows Credential
    Manager 認証依存のため、クラウド/別プラットフォームへは非移植。
  * `issue-pipeline`（スキル）＋ `issue-implementer`／`pr-reviewer`（エージェント）:
    gh CLI／Claude Code フック（`agent-command-gate.sh`）／Task 委譲／
    `bloom-model-tier` に依存する Issue 運用 dev-tooling メタパイプライン。
    **Codex CLI へは移植済み**（`.agents/skills/issue-pipeline/SKILL.md`・
    `.codex/agents/issue-implementer.toml`／`pr-reviewer.toml`）だが、
    **Copilot（`.github/`）へは非移植のまま**（gh CLI／Task 委譲／`bloom-model-tier`
    に Copilot 等価物なし）。

Both notes are scoped to the GitHub Copilot (`.github/`) tree specifically — Codex CLI
(`.codex/agents/`, `.agents/skills/`) carries real equivalents for these assets
(verified against the actual files), so exemptions are recorded per
``(name, kind, tree)``, never as a blanket per-asset exemption.

If you add a new documented non-mirror decision, first record the decision in
`.claude/tailoring-registry.md` (or the asset's own `SKILL.md`/agent `.md`), then add
the matching entry here.
"""

from __future__ import annotations

import dataclasses

from .inventory import AGENT, SKILL
from .trees import GITHUB


@dataclasses.dataclass(frozen=True)
class Exemption:
    name: str
    kind: str
    tree: str
    reason: str


_ENV_DEPENDENT = (
    "agy MCP はローカル CLI／Windows Credential Manager 認証依存のため非移植"
    "（.claude/tailoring-registry.md）"
)
_ISSUE_PIPELINE_COPILOT = (
    "gh CLI／Claude Code フック（agent-command-gate.sh）／Task 委譲／bloom-model-tier に"
    "依存する Issue 運用 dev-tooling メタパイプライン。Codex CLI へは移植済みだが Copilot"
    "（.github/）には等価物なし（.claude/tailoring-registry.md）"
)

EXEMPTIONS: tuple[Exemption, ...] = (
    Exemption("agy-delegate", SKILL, GITHUB, _ENV_DEPENDENT),
    Exemption("agy-delegate", AGENT, GITHUB, _ENV_DEPENDENT),
    Exemption("issue-pipeline", SKILL, GITHUB, _ISSUE_PIPELINE_COPILOT),
    Exemption("issue-implementer", AGENT, GITHUB, _ISSUE_PIPELINE_COPILOT),
    Exemption("pr-reviewer", AGENT, GITHUB, _ISSUE_PIPELINE_COPILOT),
)


def is_exempt(name: str, kind: str, tree: str) -> str | None:
    """Return the documented reason if `(name, kind, tree)` is a known non-mirror."""
    for exemption in EXEMPTIONS:
        if (exemption.name, exemption.kind, exemption.tree) == (name, kind, tree):
            return exemption.reason
    return None
