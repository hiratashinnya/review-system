---
description: 'Inventory .claude/ assets and hand-write GitHub Copilot equivalents (skill/prompt/agent/instructions) per type — never mass-produce instructions files.'
agent: agent
---

# 資産の横展方法確立（asset-lateral-deploy）

## 概要

`.claude/` 配下のスキル・サブエージェント・原則を、GitHub Copilot で使える形式に変換する。

**方針**：スクリプト一括変換は廃止。エージェントが資産1つずつ種別・起動方式を判断し、下表の対応に従って**手書き変換**する。
instructions の量産は禁止（エージェントは agent に、ユーザー起動コマンドは prompt/skill に振り分ける）。

---

## 振り分け決定木

| Claude Code 資産 | → Copilot 種別 | 根拠 |
|---|---|---|
| `user-invocable: false`（常時原則） | **`.github/copilot-instructions.md`** | 常時適用コンテキスト |
| `disable-model-invocation: true`（オーケストレータ） | **`.github/prompts/<name>.prompt.md`** | ユーザー `/command` 起動 |
| その他スキル（model-invocable） | **`.github/skills/<name>/SKILL.md`** | モデルが自動発見 |
| `.claude/agents/<name>.md` | **`.github/agents/<name>.agent.md`** | エージェントプロファイル |

`.instructions.md` は真にパススコープな規約のみ。**乱発禁止**。

---

## YAML フロントマター対応表

### Skill → `.github/skills/<name>/SKILL.md`

| Claude Code | Copilot SKILL.md |
|---|---|
| `name` | `name` |
| `description` | `description`（1〜2文） |
| `allowed-tools` / `disallowed-tools` | 落とす（Copilot skill にツールゲートなし） |
| `argument-hint` | 本文に記載 |

### Prompt → `.github/prompts/<name>.prompt.md`

| Claude Code | Copilot .prompt.md |
|---|---|
| `name` | `name`（省略時はファイル名） |
| `description` | `description`（single quote 推奨） |
| 実行モード | `agent: agent`（自動化手順）/ `ask`（対話）/ `edit`（編集） |
| `allowed-tools` | `tools` |
| `argument-hint` | `argument-hint` |

### Agent → `.github/agents/<name>.agent.md`

| Claude Code | Copilot .agent.md |
|---|---|
| `name` | `name` |
| `description` | `description`（**必須**・single quote 推奨） |
| `tools` | `tools`（推奨） |
| `model: opus` | `model: claude-opus-4-8`（強推奨） |
| `model: sonnet` | `model: claude-sonnet-4-6` |
| `permissionMode` / `maxTurns` 等 | 落とす |

---

## 手順

1. `.claude/skills/*/SKILL.md`・`.claude/agents/*.md`・`CLAUDE.md` を棚卸し。
2. 各資産を決定木で振り分け、一覧をチャットに提示（レビュー可能に）。
3. 対応表に従い1つずつ手書き変換。
4. `.github/` 配下に配置。
5. instructions 乱発・エージェントの誤分類がないか検算。
