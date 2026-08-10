"""Documented intentional non-mirrors — assets that legitimately have no counterpart
in a given tree, so a missing mirror there should be reported as EXEMPT, not MISSING.

This list must mirror decisions **already recorded elsewhere**, not invent new ones
(per the issue #155 task brief: "check how the repo already documents such decisions
... before inventing a new mechanism"). The source of truth is
`.claude/tailoring-registry.md`'s trailing bullet notes, as of this tool's writing:

  * `agy-delegate`（スキル＋エージェント）: agy MCP はローカル CLI／Windows Credential
    Manager 認証依存のため、クラウド/別プラットフォームへは非移植。
  * `issue-pipeline`（スキル）＋ `issue-implementer`／`issue-fixer`／`pr-reviewer`
    （エージェント）:
    gh CLI／Claude Code フック（`agent-command-gate.sh`）／Task 委譲／
    `bloom-model-tier` に依存する Issue 運用 dev-tooling メタパイプライン。
    **Codex CLI へは移植済み**（`.agents/skills/issue-pipeline/SKILL.md`・
    `.codex/agents/issue-implementer.toml`／`issue-fixer.toml`／`pr-reviewer.toml`）だが、
    **Copilot（`.github/`）へは非移植のまま**（gh CLI／Task 委譲／`bloom-model-tier`
    に Copilot 等価物なし）。`issue-fixer`（Issue #308 の是正専任ロール）はさらに
    `karte` CLI と PreToolUse フックの両方に依存するため、Copilot 側では契約が成立しない。
  * `codex-review`（スキル）: `codex` CLI／ChatGPT ログイン／`~/.codex/sessions` に
    依存する Linux/WSL 専用の「Codex 公式 CLI への第二意見レビュー委譲」入口。
    **全外部ツリー非移植**（オーナー確定 2026-07-20・.claude/tailoring-registry.md）。
    Codex CLI を Codex 自身の skill ツリー（`.agents/`）から呼ぶのは再帰的で不自然、
    Copilot（`.github/`）にも等価物なし。SKILL の applicable tree は GITHUB と
    AGENTS_DIR のみ（CODEX は agent 専用＝自動 N/A）なので、その2ツリーを exempt する。
  * `gh-create-issue`（スキル）: ユーザー指定が Codex と Claude Code の2環境に限定された
    明示スコープのため、その2環境だけに用意する。Copilot 版は作らず、将来 Copilot を
    対象化する時に形式・tool・対話境界を再評価する。

The first two assets' notes are scoped to the GitHub Copilot (`.github/`) tree
specifically — Codex CLI (`.codex/agents/`, `.agents/skills/`) carries real equivalents
for them (verified against the actual files). `codex-review` is exempt on *all* its
applicable trees. Either way exemptions are recorded per ``(name, kind, tree)``, never
as a blanket per-asset exemption.

If you add a new documented non-mirror decision, first record the decision in
`.claude/tailoring-registry.md` (or the asset's own `SKILL.md`/agent `.md`), then add
the matching entry here.
"""

from __future__ import annotations

import dataclasses

from .inventory import AGENT, SKILL
from .trees import AGENTS_DIR, GITHUB


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
_ISSUE_FIXER_COPILOT = (
    "Issue 運用パイプラインの是正専任ロール（Issue #308）。親パイプラインと同じ理由で Copilot"
    "（.github/）には等価物が無く、さらに karte CLI と PreToolUse フック（agent-command-gate.sh の"
    "GATED_ROLES / PYTHON_MODULES_BY_ROLE）の両方に依存するため Copilot 側では契約が成立しない。"
    "Codex CLI へは移植済み（.claude/tailoring-registry.md）"
)
_CODEX_REVIEW_ENV = (
    "codex CLI／ChatGPT ログイン／~/.codex/sessions に依存する Linux/WSL 専用の第二意見"
    "レビュー委譲。全外部ツリー非移植（Codex CLI を Codex 自身の skill から呼ぶ再帰性が不自然・"
    "Copilot にも等価物なし）（.claude/tailoring-registry.md）"
)
_GH_CREATE_ISSUE_COPILOT = (
    "ユーザー指定が Codex と Claude Code の2環境に限定された明示スコープのため Copilot 版は"
    "作らない。将来 Copilot を対象化する時に形式・tool・対話境界を再評価する"
    "（.claude/tailoring-registry.md）"
)

EXEMPTIONS: tuple[Exemption, ...] = (
    Exemption("agy-delegate", SKILL, GITHUB, _ENV_DEPENDENT),
    Exemption("agy-delegate", AGENT, GITHUB, _ENV_DEPENDENT),
    Exemption("issue-pipeline", SKILL, GITHUB, _ISSUE_PIPELINE_COPILOT),
    Exemption("issue-implementer", AGENT, GITHUB, _ISSUE_PIPELINE_COPILOT),
    Exemption("issue-fixer", AGENT, GITHUB, _ISSUE_FIXER_COPILOT),
    Exemption("pr-reviewer", AGENT, GITHUB, _ISSUE_PIPELINE_COPILOT),
    Exemption("codex-review", SKILL, GITHUB, _CODEX_REVIEW_ENV),
    Exemption("codex-review", SKILL, AGENTS_DIR, _CODEX_REVIEW_ENV),
    Exemption("gh-create-issue", SKILL, GITHUB, _GH_CREATE_ISSUE_COPILOT),
)


def is_exempt(name: str, kind: str, tree: str) -> str | None:
    """Return the documented reason if `(name, kind, tree)` is a known non-mirror."""
    for exemption in EXEMPTIONS:
        if (exemption.name, exemption.kind, exemption.tree) == (name, kind, tree):
            return exemption.reason
    return None
