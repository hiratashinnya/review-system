---
name: asset-lateral-deploy
description: 資産の横展方法確立。.claude 配下のスキル/サブエージェント/原則を棚卸しし、ターゲットプラットフォーム（GitHub Copilot 等）向けに「エージェントが都度判断して手書き変換」する。種別ごとの対応表に従い、スキル/プロンプト/エージェント/instructions を取り違えない。
disable-model-invocation: true
---

# 資産の横展方法確立（asset-lateral-deploy）

## 概要

`.claude/` 配下の**スキル・サブエージェント・原則**を、GitHub Copilot など別プラットフォームで使える形式に変換する。

**方針（2026-06-15 改定）**：**スクリプト一括変換は廃止**。エージェントが**資産1つずつ種別・起動方式を判断し、下表の対応に従って手書き変換**する。
理由＝旧スクリプト方式は全サブエージェントを `.instructions.md` に量産し、Copilot の「instructions＝自動適用の常時コンテキスト」という意味を取り違えていた。**instructions の量産は禁止**（エージェントは agent に、ユーザー起動コマンドは prompt/skill に振り分ける）。

> 旧スクリプト `scripts/lateral_deploy.py`（とそのテスト）は本方針改定で**削除済み**（オーナー判断・2026-06-15）。一括変換は instructions 量産を招くため廃し、エージェント手書きに一本化した。

---

## 大原則：種別を取り違えない（最重要）

Copilot には Claude Code と対応する **4 種**のカスタマイズ実体がある。**起動方式（誰がいつ呼ぶか）で機械的に振り分ける**。

| Copilot 実体 | 何者か | 誰が起動 | Claude Code の対応元 |
|---|---|---|---|
| **Skill**（`.github/skills/<name>/SKILL.md`） | モデルが description で**自動発見**して読み込む能力（progressive disclosure・バンドル資産可） | モデル（自動） | model-invocable な `.claude/skills/`（資産バンドルあり優先） |
| **Prompt**（`.github/prompts/<name>.prompt.md`） | ユーザーが `/<name>` で**明示起動**する手順テンプレ | ユーザー（`/command`） | `disable-model-invocation: true` の `.claude/skills/`（オーケストレータ／パイプライン） |
| **Agent**（`.github/agents/<name>.agent.md`） | ツール/MCP を絞った**専門エージェントプロファイル** | エージェント選択／委譲 | `.claude/agents/`（サブエージェント） |
| **Instructions**（`.github/instructions/<name>.instructions.md` ＋ `.github/copilot-instructions.md`） | `applyTo` glob で**自動適用**される常時コンテキスト（起動概念なし） | 自動（パターン一致時） | 常時ロードの原則・規約（`user-invocable: false`、`spec-principles`、`CLAUDE.md`） |

**振り分け決定木（`.claude/skills/*` の場合）**：
1. `user-invocable: false`（常時原則。例 `spec-principles`） → **Instructions**（`copilot-instructions.md` に展開）。**skill/prompt にしない**。
2. `disable-model-invocation: true`（ユーザー起動オーケストレータ。例 `/asset-lateral-deploy`, `/impl-design-pipeline`） → **Prompt**。
3. それ以外（モデルが自動発見すべき能力。バンドル資産があればなお skill 向き） → **Skill**。

**`.claude/agents/*` は必ず Agent へ**（instructions に流さない）。**`CLAUDE.md` は `copilot-instructions.md` へ**。

---

## YAML フロントマター対応表（公式仕様準拠）

> 出典は本文末尾「参考（公式ドキュメント）」。フィールド名のハイフン有無まで公式に合わせること。

### A. Skill → Skill（`.claude/skills/<name>/SKILL.md` → `.github/skills/<name>/SKILL.md`）

| Claude Code | GitHub Copilot | 変換メモ |
|---|---|---|
| `name` | `name` | そのまま |
| `description` | `description` | 「何を・いつ使うか」を1〜2文に。Copilot もこれで自動発見する |
| `when_to_use` | （`description` に畳み込む） | Copilot SKILL.md に専用欄なし |
| `allowed-tools` / `disallowed-tools` | （なし） | Copilot skill はツールゲートを持たない。落とす |
| `argument-hint` / `arguments` | （本文に手順記載） | Copilot skill は引数前提でないため本文で説明 |
| バンドル（`scripts/` `references/` `assets/`） | 同名フォルダごと移植 | **skill だけが資産バンドルを持てる**。skill に寄せる根拠 |

本文（Markdown body）はそのまま移植可。相対リンクは `.github/skills/<name>/` 基準に貼り直す。

### B. Skill（オーケストレータ）→ Prompt（`disable-model-invocation: true` → `.github/prompts/<name>.prompt.md`）

| Claude Code | GitHub Copilot | 変換メモ |
|---|---|---|
| `name` | `name` | 省略時はファイル名が `/command` 名 |
| `description` | `description` | 単一文・single quote 推奨 |
| （実行モード） | `agent: agent` | 自動化したい手順は `agent`。対話だけなら `ask`、編集中心なら `edit`、カスタム agent 名も可 |
| `allowed-tools` | `tools` | 使うツール/ツールセットを列挙 |
| `argument-hint` | `argument-hint` | そのまま |
| `model` | `model` | エイリアス差異に注意（Copilot の選択モデル名に合わせる） |

### C. Subagent → Agent（`.claude/agents/<name>.md` → `.github/agents/<name>.agent.md`）

| Claude Code | GitHub Copilot | 変換メモ |
|---|---|---|
| `name` | `name` | 任意。小文字＋ハイフン |
| `description` | `description` | **必須**・single quote 推奨。委譲判断に使われる |
| `tools` | `tools` | 推奨。MCP 連携時は特に明示 |
| `model` | `model` | **強推奨**。Claude の `opus/sonnet/haiku` は Copilot 側の対応モデル名へ読み替え |
| `permissionMode` / `maxTurns` / `memory` 等 | （なし） | Copilot に対応概念なし。落とすか本文に注記 |
| （なし） | `target` | 任意（`vscode` / `github-copilot`）。両対応なら省略 |

本文（システムプロンプト）はそのまま移植。

### D. 常時原則 → Instructions（`user-invocable: false` / `CLAUDE.md` → `.github/copilot-instructions.md`）

| Claude Code | GitHub Copilot | 変換メモ |
|---|---|---|
| `spec-principles`（PR1–PR10） | `.github/copilot-instructions.md` に**インライン展開** | 常時適用したい中核原則 |
| `CLAUDE.md` の作業規約 | `.github/copilot-instructions.md`（または `AGENTS.md`） | プロジェクト全体の常時ルール |
| 特定パスだけに効かせたい規約 | `.github/instructions/<name>.instructions.md` ＋ `applyTo: '<glob>'` | **本当にパススコープな場合のみ**作る。乱発禁止 |

`.instructions.md` のフロントマターは `description` と `applyTo`（glob）のみ。

---

## 手順（エージェントが手書き）

1. **棚卸し**：`.claude/skills/*/SKILL.md`・`.claude/agents/*.md`・`CLAUDE.md` を列挙。必要なら `asset-auditor` で重複/矛盾を点検。
2. **振り分け表を作る**：各資産を上の決定木で skill / prompt / agent / instructions に分類し、チャットに一覧提示（取り違え防止のためレビュー可能に）。
3. **1つずつ手書き変換**：対応表（A–D）に従い、フロントマターを正しいフィールドに写し替え、本文を移植。**機械一括せず、各資産の意図に合わせて整える**。
4. **配置**：`.github/skills/<name>/SKILL.md`・`.github/prompts/<name>.prompt.md`・`.github/agents/<name>.agent.md`・`.github/copilot-instructions.md`（＋必要時のみ `.github/instructions/`）。
5. **検算**：instructions が乱発されていないか／サブエージェントが agent になっているか／オーケストレータが prompt になっているかを確認。
6. PR は**ユーザーが明示依頼したときのみ**作成。

---

## Done 条件

- ✓ 各 `.claude/` 資産が決定木どおり skill / prompt / agent / instructions に分類され、一覧がレビュー済み。
- ✓ サブエージェントは `.github/agents/*.agent.md` に変換（**instructions に流していない**）。
- ✓ ユーザー起動オーケストレータは `.github/prompts/*.prompt.md`、モデル自動発見の能力は `.github/skills/*/SKILL.md`。
- ✓ 常時原則（spec-principles / CLAUDE.md）のみ `.github/copilot-instructions.md` に展開。`.instructions.md` は真にパススコープなものに限定。
- ✓ 各フロントマターが対応表のフィールド名（ハイフン有無含む）どおり。

---

## 参考（公式ドキュメント・要確認）

対応表は以下の公式仕様に基づく。改定時は再確認すること。

**GitHub Copilot**
- Custom agents（`.github/agents/*.agent.md`）: https://code.visualstudio.com/docs/agent-customization/custom-agents ／ https://docs.github.com/en/copilot/reference/custom-agents-configuration
- Prompt files（`.github/prompts/*.prompt.md`）: https://code.visualstudio.com/docs/agent-customization/prompt-files
- Custom instructions（`.github/instructions/*.instructions.md` ・ `copilot-instructions.md`）: https://code.visualstudio.com/docs/agent-customization/custom-instructions
- Agent Skills（`.github/skills/<name>/SKILL.md`・2025-12-18 GA）: https://code.visualstudio.com/docs/agent-customization/agent-skills ／ https://github.blog/changelog/2025-12-18-github-copilot-now-supports-agent-skills/

**Claude Code**
- Skills（`.claude/skills/<name>/SKILL.md`）: https://code.claude.com/docs/en/skills
- Subagents（`.claude/agents/<name>.md`）: https://code.claude.com/docs/en/sub-agents
