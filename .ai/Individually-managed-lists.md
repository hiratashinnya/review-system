# Issue #406 資産対応表

この表は 2026-08-21 に共有ワークツリーの実在ファイルを調査した結果である。`<name>` は表中の資産名に置き換える。ここにないファイルの存在は仮定しない。

## 共通本文（SoT）

### Skills

| 名前 | 共通本文 |
|---|---|
| `align` | [` .ai/skills/align/SKILL.md`](skills/align/SKILL.md) |
| `architecture-design` | [` .ai/skills/architecture-design/SKILL.md`](skills/architecture-design/SKILL.md) |
| `asset-lateral-deploy` | [` .ai/skills/asset-lateral-deploy/SKILL.md`](skills/asset-lateral-deploy/SKILL.md) |
| `asset-pipeline` | [` .ai/skills/asset-pipeline/SKILL.md`](skills/asset-pipeline/SKILL.md) |
| `bloom-model-tier` | [` .ai/skills/bloom-model-tier/SKILL.md`](skills/bloom-model-tier/SKILL.md) |
| `codex-review` | [` .ai/skills/codex-review/SKILL.md`](skills/codex-review/SKILL.md) |
| `coverage-html` | [` .ai/skills/coverage-html/SKILL.md`](skills/coverage-html/SKILL.md) |
| `docidx` | [` .ai/skills/docidx/SKILL.md`](skills/docidx/SKILL.md) |
| `domain-model` | [` .ai/skills/domain-model/SKILL.md`](skills/domain-model/SKILL.md) |
| `gh-create-issue` | [` .ai/skills/gh-create-issue/SKILL.md`](skills/gh-create-issue/SKILL.md) |
| `impl-design-pipeline` | [` .ai/skills/impl-design-pipeline/SKILL.md`](skills/impl-design-pipeline/SKILL.md) |
| `issue-pipeline` | [` .ai/skills/issue-pipeline/SKILL.md`](skills/issue-pipeline/SKILL.md) |
| `mvp-scope` | [` .ai/skills/mvp-scope/SKILL.md`](skills/mvp-scope/SKILL.md) |
| `orchestration-design` | [` .ai/skills/orchestration-design/SKILL.md`](skills/orchestration-design/SKILL.md) |
| `prompt-design` | [` .ai/skills/prompt-design/SKILL.md`](skills/prompt-design/SKILL.md) |
| `schema-design` | [` .ai/skills/schema-design/SKILL.md`](skills/schema-design/SKILL.md) |
| `spec-pipeline` | [` .ai/skills/spec-pipeline/SKILL.md`](skills/spec-pipeline/SKILL.md) |
| `spec-principles` | [` .ai/skills/spec-principles/SKILL.md`](skills/spec-principles/SKILL.md) |
| `test-strategy` | [` .ai/skills/test-strategy/SKILL.md`](skills/test-strategy/SKILL.md) |
| `value-trace` | [` .ai/skills/value-trace/SKILL.md`](skills/value-trace/SKILL.md) |

### Agents

| 名前 | 共通本文 |
|---|---|
| `analysis-author` | [` .ai/agents/analysis-author.md`](agents/analysis-author.md) |
| `asset-auditor` | [` .ai/agents/asset-auditor.md`](agents/asset-auditor.md) |
| `authoring-fanout` | [` .ai/agents/authoring-fanout.md`](agents/authoring-fanout.md) |
| `design-author` | [` .ai/agents/design-author.md`](agents/design-author.md) |
| `doc-system-config-operator` | [` .ai/agents/doc-system-config-operator.md`](agents/doc-system-config-operator.md) |
| `doc-system-v2-authoring` | [` .ai/agents/doc-system-v2-authoring.md`](agents/doc-system-v2-authoring.md) |
| `dsv2-lookup` | [` .ai/agents/dsv2-lookup.md`](agents/dsv2-lookup.md) |
| `issue-fixer` | [` .ai/agents/issue-fixer.md`](agents/issue-fixer.md) |
| `issue-implementer` | [` .ai/agents/issue-implementer.md`](agents/issue-implementer.md) |
| `pr-reviewer` | [` .ai/agents/pr-reviewer.md`](agents/pr-reviewer.md) |
| `reconciliation-validator` | [` .ai/agents/reconciliation-validator.md`](agents/reconciliation-validator.md) |
| `reconciliation` | [` .ai/agents/reconciliation.md`](agents/reconciliation.md) |
| `requirements-author` | [` .ai/agents/requirements-author.md`](agents/requirements-author.md) |
| `spec-author` | [` .ai/agents/spec-author.md`](agents/spec-author.md) |
| `spec-inspector` | [` .ai/agents/spec-inspector.md`](agents/spec-inspector.md) |
| `structured-analysis` | [` .ai/agents/structured-analysis.md`](agents/structured-analysis.md) |
| `verification-author` | [` .ai/agents/verification-author.md`](agents/verification-author.md) |

### Rationale

| 名前 | 共有経緯本文 |
|---|---|
| `issue-fixer` | [` .ai/rationale/issue-fixer.md`](rationale/issue-fixer.md) |
| `issue-implementer` | [` .ai/rationale/issue-implementer.md`](rationale/issue-implementer.md) |
| `issue-pipeline` | [` .ai/rationale/issue-pipeline.md`](rationale/issue-pipeline.md) |
| `pr-reviewer` | [` .ai/rationale/pr-reviewer.md`](rationale/pr-reviewer.md) |
| 索引・分離規則 | [` .ai/rationale/README.md`](rationale/README.md) |

## PF wrapper / metadata の実在対応

### Skills

| PF tree | wrapper / metadata パス | 確認できた対応範囲・未配置 |
|---|---|---|
| Claude | `.claude/skills/<name>/SKILL.md` | 上記20 Skill 全て。`agy-delegate` は `.ai` 共通一覧にない Claude 固有 Skill。 |
| Review-system repo skills | `.agents/skills/<name>/SKILL.md` | `codex-review` を除く上記19 Skill。`agy-delegate` と `doc-system-config` は `.ai` 共通一覧にない repo 固有 Skill。`gh-create-issue/agents/openai.yaml` と `issue-pipeline/agents/openai.yaml` も実在する PF metadata。 |
| GitHub Copilot | `.github/skills/<name>/SKILL.md` | `align`、`architecture-design`、`bloom-model-tier`、`coverage-html`、`docidx`、`domain-model`、`impl-design-pipeline`、`issue-pipeline`、`mvp-scope`、`orchestration-design`、`prompt-design`、`schema-design`、`test-strategy`、`value-trace`。 |
| GitHub Copilot | `.github/prompts/<name>.prompt.md` | `asset-lateral-deploy`、`asset-pipeline`、`impl-design-pipeline`、`spec-pipeline`。Copilot では明示起動オーケストレータを Prompt に分類している。 |
| GitHub Copilot | `.github/copilot-instructions.md` | `spec-principles` はこの常時 Instructions に PR1–PR10 のインライン本文として配置している。今回 `.ai/skills/spec-principles/SKILL.md` への参照化は行っていない。`.github/skills/spec-principles/`、`gh-create-issue/`、`codex-review/` は今回の調査では確認できない。 |

Codex は repo Skill を `.agents/skills/` から探索するため、`.codex/skills/` は作っていない。`.codex/agents/` は次表の Agent metadata 用である。

### Agents

| PF tree | wrapper / metadata パス | 確認できた対応範囲・未配置 |
|---|---|---|
| Claude | `.claude/agents/<name>.md` | `doc-system-config-operator` を除く上記16 Agent。`agy-delegate` は `.ai` 共通一覧にない Claude 固有 Agent。 |
| Codex | `.codex/agents/<name>.toml` | 上記17 Agent 全て。`agy-delegate.toml` は `.ai` 共通一覧にない Codex 固有 Agent。 |
| GitHub Copilot | `.github/agents/<name>.agent.md` | `analysis-author`、`asset-auditor`、`authoring-fanout`、`design-author`、`doc-system-v2-authoring`、`dsv2-lookup`、`reconciliation-validator`、`reconciliation`、`requirements-author`、`spec-author`、`spec-inspector`、`structured-analysis`、`verification-author`。`doc-system-config-operator`、`issue-fixer`、`issue-implementer`、`pr-reviewer` はこの tree では未確認。 |

### Rationale の互換ポインタ

`.claude/rationale/README.md` と `.claude/rationale/{issue-fixer,issue-implementer,issue-pipeline,pr-reviewer}.md` は実在するが、各1行の `.ai/rationale/` への互換ポインタである。`.ai/rationale/` に重複した正本を置かない。`.agents`、`.codex`、`.github` に対応する rationale ファイルは今回の調査では確認できない。

## PF 固有差分を残す理由

| PF | wrapper / metadata に残る差分 | 差分を残す理由 |
|---|---|---|
| Claude | `.claude/agents/*.md` の `tools`・`model`・一部 `effort` frontmatter。`issue-pipeline`、`impl-design-pipeline`、`issue-fixer`、`issue-implementer`、`pr-reviewer` などに Claude の Task/Agent、worktree、hook、context-mode 契約。 | Claude Code の loader と dispatch、許可ツール、hook gate がこの形式を読むため。 |
| Codex | `.codex/agents/*.toml` は `name`・`description`・`developer_instructions` を持つ。`.codex/agents/README.md` の方針どおり source-platform-only の `tools`・`model` frontmatter は TOML に複製しない。権限境界は `.codex/hooks/agent-command-gate.sh` 等で実装し、Codex 固有の `spawn_agent`、commit/push/merge gate を本文へ追記する。 | Codex custom-agent の形式と実行時 permission gate が Claude の frontmatter と異なるため。権限を共通本文へ混ぜると PF の deny/allow を誤って共有するため。 |
| GitHub Copilot | `.github/agents/*.agent.md` の `model`・`tools` frontmatter、`Skill` / `Prompt` / `Agent` / `Instructions` の分類。`asset-lateral-deploy`、`asset-pipeline`、`spec-pipeline` は Prompt、`issue-pipeline` は Skill として存在する。 | Copilot はユーザー明示起動・自動発見・専門 Agent・常時適用で起動契約が異なるため。Agent が存在しない Issue 実行系をあるものとして記録しないため。 |
| Review-system repo skills | `.agents/skills/<name>/SKILL.md` は repo-scoped Skill の metadata と共通本文ポインタ。`impl-design-pipeline` と `issue-pipeline` には Codex の agent/worktree 差分が残る。 | Codex CLI の repo Skill 探索入口であり、Claude/Copilot の Agent metadata とは別の loader を使うため。 |

## rules / hooks / instructions の扱い

Issue #406 では次のファイル群を移行・変更しない。ここは実行時の安全境界または PF の常時適用契約であり、Skill/Agent の共通本文化と同じ変更として扱わない。

| 種別 | 現在の配置 | 今回の扱い |
|---|---|---|
| プロジェクト指示 | `AGENTS.md`、`CLAUDE.md` | 移行・変更なし |
| Claude rules | `.claude/rules/*.md` | 移行・変更なし |
| Claude hooks | `.claude/hooks/` | 移行・変更なし |
| Codex hooks / 設定 | `.codex/hooks/`、`.codex/config.toml`、`.codex/hooks.json` | 移行・変更なし |
| Copilot 常時 Instructions | `.github/copilot-instructions.md` | 移行・変更なし |
| PF metadata / workflows | `.agents/README.md`、`.codex/README.md`、`.github/workflows/` | 移行・変更なし |

`spec-principles` の共通本文 SoT は [`.ai/skills/spec-principles/SKILL.md`](skills/spec-principles/SKILL.md) である。Copilot instructions の将来の参照化は、owner review 後に選択できる別スコープとする。

Owner review 用の今後の選択肢は次のとおり。

| 選択肢 | 内容 | 推奨 |
|---|---|---|
| A（現状維持） | 実行境界は各 PF の rules/hooks/instructions に置き、`.ai` は Skill/Agent/rationale の共通本文だけを持つ。 | **Issue #406 ではこれを推奨**。既存の deny/allow と自動適用範囲を壊さない。 |
| B（段階的共有） | 重複する prose だけを別 Issue で `.ai` に抽出し、実行可能な hook、PF metadata、入口ファイルは各 tree に残す。 | 将来の重複削減案。owner が対象範囲と機械ゲートをレビューしてから着手する。 |
| C（全面集約） | rules/instructions まで `.ai` の共通本文に集約し、各 PF wrapper から参照する。 | 非推奨。PF ごとの起動・権限・常時適用 semantics を失うリスクが高く、別設計が必要。 |

## 保守ルール

- 共通の規範本文を変更するときは、まず対応する `.ai` ファイルを変更し、PF wrapper は必要な metadata/差分だけ更新する。
- rationale は `.ai/rationale/` だけを正本とし、`.claude/rationale/` を本文の編集先にしない。
- PF にだけ存在する asset、PF 固有の未配置、rules/hooks/instructions の変更は、共通本文の移設と混ぜず、owner review を経た別スコープとして扱う。
