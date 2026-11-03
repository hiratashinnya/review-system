"""Documented intentional non-mirrors — assets that legitimately have no counterpart
in a given tree, so a missing mirror there should be reported as EXEMPT, not MISSING.

This list must mirror decisions **already recorded elsewhere**, not invent new ones
(per the issue #155 task brief: "check how the repo already documents such decisions
... before inventing a new mechanism"). The source of truth is
`.claude/tailoring-registry.md`'s trailing bullet notes; each entry's reason string
below cites the decision it transcribes (the registry holds the full rationale; per-entry history: `.ai/rationale/asset-parity-exceptions.md`).

Exemptions are recorded per ``(name, kind, tree)``, never as a blanket per-asset
exemption: most entries are scoped to the GitHub Copilot (`.github/`) tree because
Codex CLI carries real equivalents, while `codex-review` is exempt on *all* its
applicable trees. A `user-invocable: false` skill that is neither really inlined into
`copilot-instructions.md` (`inlining.py`) nor listed here is reported MISSING.

If you add a new documented non-mirror decision, first record the decision in
`.claude/tailoring-registry.md` (or the asset's own `SKILL.md`/agent `.md`), then add
the matching entry here.
"""

from __future__ import annotations

import dataclasses

from .inventory import AGENT, SKILL
from .trees import AGENTS_DIR, CODEX, GITHUB


@dataclasses.dataclass(frozen=True)
class Exemption:
    name: str
    kind: str
    tree: str
    reason: str


from .exemption_reasons import (
    _ENV_DEPENDENT,
    _ISSUE_PIPELINE_AGENT_COPILOT,
    _ISSUE_FIXER_COPILOT,
    _ISSUE_PIPELINE_CODEX_RETIRED,
    _ISSUE_PIPELINE_SKILL_RETIRED,
    _CODEX_REVIEW_ENV,
    _GH_CREATE_ISSUE_COPILOT,
    _GH_CREATE_ISSUE_AGENT_CLAUDE_ONLY,
    _SILENT_FAILURE_DIAGNOSIS_COPILOT,
)

EXEMPTIONS: tuple[Exemption, ...] = (
    Exemption("agy-delegate", SKILL, GITHUB, _ENV_DEPENDENT),
    Exemption("agy-delegate", AGENT, GITHUB, _ENV_DEPENDENT),
    Exemption("issue-implementer", AGENT, GITHUB, _ISSUE_PIPELINE_AGENT_COPILOT), Exemption("issue-implementer", AGENT, CODEX, _ISSUE_PIPELINE_CODEX_RETIRED),
    Exemption("issue-fixer", AGENT, GITHUB, _ISSUE_FIXER_COPILOT), Exemption("issue-fixer", AGENT, CODEX, _ISSUE_PIPELINE_CODEX_RETIRED),
    Exemption("pr-reviewer", AGENT, GITHUB, _ISSUE_PIPELINE_AGENT_COPILOT), Exemption("pr-reviewer", AGENT, CODEX, _ISSUE_PIPELINE_CODEX_RETIRED),
    Exemption("issue-pipeline", SKILL, AGENTS_DIR, _ISSUE_PIPELINE_SKILL_RETIRED),
    Exemption("codex-review", SKILL, GITHUB, _CODEX_REVIEW_ENV),
    Exemption("codex-review", SKILL, AGENTS_DIR, _CODEX_REVIEW_ENV),
    Exemption("gh-create-issue", SKILL, GITHUB, _GH_CREATE_ISSUE_COPILOT),
    Exemption("gh-create-issue", AGENT, GITHUB, _GH_CREATE_ISSUE_AGENT_CLAUDE_ONLY),
    Exemption("gh-create-issue", AGENT, CODEX, _GH_CREATE_ISSUE_AGENT_CLAUDE_ONLY),
    Exemption("silent-failure-diagnosis", SKILL, GITHUB, _SILENT_FAILURE_DIAGNOSIS_COPILOT),
    Exemption("review-harm", SKILL, GITHUB, "Copilot の専用 reviewer 未移植。pipeline が正本を必読（.claude/tailoring-registry.md）"),
)

EXEMPTIONS += tuple(Exemption(role, AGENT, tree, reason)
    for role in ("issue-investigator", "ac-designer", "change-planner", "plan-reviewer", "test-writer", "adviser")
    for tree, reason in ((GITHUB, _ISSUE_PIPELINE_AGENT_COPILOT), (CODEX, _ISSUE_PIPELINE_CODEX_RETIRED)))

def is_exempt(name: str, kind: str, tree: str) -> str | None:
    """Return the documented reason if `(name, kind, tree)` is a known non-mirror."""
    for exemption in EXEMPTIONS:
        if (exemption.name, exemption.kind, exemption.tree) == (name, kind, tree):
            return exemption.reason
    return None


# Reverse-direction decisions: these are present without a Claude parity seed.
MIRROR_ONLY: tuple[Exemption, ...] = (
    Exemption("doc-system-v2-authoring", AGENT, GITHUB,
              "Shared author contract; non-invocable template (.ai/agents/doc-system-v2-authoring.md; Copilot template frontmatter)"),
    Exemption("doc-system-v2-authoring", AGENT, CODEX,
              "Shared author contract reference (.ai/agents/doc-system-v2-authoring.md; .codex/agents/doc-system-v2-authoring.toml)"),
    Exemption("doc-system-config", SKILL, AGENTS_DIR,
              "Codex-only skill (.ai/Individually-managed-lists.md; .ai/rationale/doc-system-config.md)"),
)

def mirror_only_reason(name: str, kind: str, tree: str) -> str | None:
    """Return the reason for an exact documented mirror-only key."""
    return next((entry.reason for entry in MIRROR_ONLY
                 if (entry.name, entry.kind, entry.tree) == (name, kind, tree)), None)
