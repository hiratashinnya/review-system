# PF 個別管理リスト

共通本文の一覧は載せず、PF（Claude Code／Codex CLI／GitHub Copilot／Repo-skill）の loader・wrapper・実行メタデータに生じる差分だけを記録する。共通本文の SoT は `.ai/README.md` の配置規則に従う。

## loader 差分

| PF | loader 入口 | 個別形式 |
|---|---|---|
| Claude Code | `.claude/skills/`、`.claude/agents/` | YAML frontmatter。Agent wrapper に `tools`、`model`、任意の `effort`／`skills` を置く。 |
| Codex CLI | `.agents/skills/`、`.codex/agents/` | repo-skill は Markdown、custom agent は TOML（`name`／`description`／`developer_instructions`）。Claude の frontmatter を複製しない。 |
| GitHub Copilot | `.github/skills/`、`.github/prompts/`、`.github/agents/`、`.github/copilot-instructions.md` | Skill／Prompt／Agent／Instructions の loader に分かれる。Agent は YAML frontmatter の `model`／`tools` を使う。常駐入口は共通 guidance と Copilot 固有原稿から生成する。 |
| Repo-skill | `.agents/skills/` | Codex CLI の repo-scoped skill discovery 用。Agent の配置先ではない。 |

## Bloom の model mapping

| PF | mapping |
|---|---|
| Claude Code | `model:` は `haiku`／`sonnet`／`opus`。PF上限の差分として、共通の最大の推論予算だけ `effort: xhigh` へ畳む。 |
| GitHub Copilot | 中位モデル層→`claude-sonnet-5`、最上位モデル層→`claude-opus-4-8`。共通の予算は frontmatter で表現できず、モデルIDだけを写像する。低位モデル層は live の利用可能 ID を確認できた場合だけ指定し、確認できなければ架空 ID を追加せず STOP してオーナー確認を求める。Claude の `effort` や Codex の推論予算キーは持ち込まない。 |
| Codex CLI／Repo-skill | 低位／中位モデル層→`gpt-5.6-luna`、最上位モデル層→`gpt-5.6-sol`。共通の最小／小／中／大／最大を session/config の `model_reasoning_effort: low`／`medium`／`high`／`xhigh`／`max` へ一対一に写像する。`.codex/agents/*.toml` は session 設定を継承して `model` や予算キーを複製しない。 |

## 個別配置・非移植

- `codex-review` は `.claude/skills/codex-review/SKILL.md` の Claude 専用。`codex exec`、ChatGPT login、Linux/WSL の session に依存するため、Codex／Copilot／Repo-skill へは配置しない。
- `agy-delegate` は Claude では `.claude/skills/agy-delegate/SKILL.md` から `.claude/agents/agy-delegate.md` へ委譲し、具体的な MCP tool metadata と Claude 固有の返却手段を持つ。Codex では `.agents/skills/agy-delegate/SKILL.md` から `.codex/agents/agy-delegate.toml` へ委譲し、利用可能な agy MCP 能力を session で解決する。ローカル CLI／Windows Credential Manager に依存するため Copilot へは移植しない。
- `gh-create-issue` は Claude と Repo-skill（`.agents/skills/gh-create-issue/SKILL.md`）に実在する。Copilot 版は作らない。GitHub 変更の明示依頼境界と loader/tool 差分を対象 PF 限定で管理する。
- `issue-fixer`／`issue-implementer`／`pr-reviewer` は Claude と Codex に実在する。Copilot Agent 版は非移植。Claude hook、Task、gh CLI、`karte`、ロール別 push／merge 境界を Copilot で同一契約にできないため。

## 追加 wrapper

`doc-system-config-operator` は共通本文を各 loader 形式へ変換した wrapper を追加している。

- Claude: `.claude/agents/doc-system-config-operator.md`（`tools`／`model`／`skills`）
- Codex: `.codex/agents/doc-system-config-operator.toml`（`name`／`description`／`developer_instructions`）
- Copilot: `.github/agents/doc-system-config-operator.agent.md`（`model`／`tools`）

関連手順の `doc-system-config` skill は Codex の repo-skill 入口 `.agents/skills/doc-system-config/SKILL.md` にのみ配置する。共通 Agent 本文はこの Codex 固定 path を参照せず、Claude／Codex／Copilot の各 wrapper 入口を維持する。Claude／Copilot に同名 skill を複製しない。

## PF 固有の実行差分

- Claude は Task/Agent dispatch、`isolation: "worktree"`、`issue-start-gate.sh` 等の hook、ロール別 command gate を持つ。
- Codex は `spawn_agent`、`.codex/hooks.json`、PreToolUse の `agent-command-gate.sh`、Stop hook／rate-limit recovery を持つ。Claude の worktree bind/stop hook は配置しない。
- Copilot は Prompt の明示起動と Agent の選択・委譲を使う。Claude/Codex 相当の project hook、PreToolUse、worktree bind は配置しない。

## Hook 構成一覧

**確認日時**: 2026-08-25T23:22:05+00:00
**調査時 commit**: `fadf57602fd87cd55b86ae7690ffbe1dd8faaa4f`

### ライフサイクル hook 一覧（PF 別適用有無）

| # | ライフサイクル hook | 呼び出し実体 | Claude Code | Codex CLI | Copilot |
|---|---|---|:---:|:---:|:---:|
| 1 | PreToolUse（Bash／merge 系） | `pr-merge-gate.sh` | ✅ | ✅ | — |
| 2 | PreToolUse（Bash） | `agent-command-gate.sh` | ✅ | ✅ | — |
| 3 | PreToolUse（ctx_execute 系） | `agent-command-gate.sh` | ✅ | — | — |
| 4 | PreToolUse（Task／spawn_agent） | `issue-start-gate.sh` | ✅ | ✅ | — |
| 5 | PostToolUse（Bash／merge 系） | `pr-merge-gate.sh` | ✅ | ✅ | — |
| 6 | PostToolUse（Write／Edit） | `check-governance-drift.sh` | ✅ | — | — |
| 7 | SubagentStart（issue-fixer） | `subagent-karte-inject.sh` | ✅ | — | — |
| 8 | SubagentStart（implementer／fixer） | `subagent-worktree-bind.sh` | ✅ | — | — |
| 9 | SubagentStop（implementer／fixer） | `subagent-stop-gate.sh` | ✅ | — | — |
| 10 | StopFailure（rate_limit） | `on-rate-limit.sh` | ✅ | — | — |
| 11 | Stop | `codex-rate-limit-stop-hook.sh` | — | ✅ | — |
| 12 | UserPromptSubmit | `inject-governance.sh` | ✅ | — | — |
| 13 | SessionStart（startup／resume） | `install_pkgs.sh` | ✅ | — | — |
| 14 | SessionStart（startup／clear／compact） | `orchestrator-context.sh` | ✅ | — | — |

> Copilot はリポジトリ固有のライフサイクル hook に非対応（`.ai/guidance/platforms/copilot.md` で確認済み）。

### 各 hook の概要

#### 1・5. pr-merge-gate

- **概要**: PR merge 前に blocker evidence を検査し、未解消なら merge 操作を拒否する。PostToolUse 側では merge 応答を記録する。
- **スコープ**: Bash・merge 系 MCP ツール呼び出し。
- **PF 間差異**: Claude（`.claude/hooks/pr-merge-gate.sh`）と Codex（`.codex/hooks/pr-merge-gate.sh`）で個別実装。matcher のツール名が PF の MCP 体系に合わせて異なる。
- **実装構成**: [`.claude/hooks/README.md`](.claude/hooks/README.md)、[`.codex/hooks/README.md`](.codex/hooks/README.md)

#### 2–3. agent-command-gate

- **概要**: ロール別（`issue-implementer`／`issue-fixer`／`pr-reviewer`）に push／merge 等の操作を非対称に制限する。ctx_execute 系 MCP ツールにも拡張済み（Issue #303）。
- **スコープ**: Bash、context-mode 実行系ツール。
- **PF 間差異**: Claude は Bash＋ctx_execute 系の2 matcher。Codex は Bash のみ（ctx_execute 系は Codex に未導入）。
- **実装構成**: [`.claude/hooks/agent-command-gate.sh`](.claude/hooks/agent-command-gate.sh)、[`.codex/hooks/agent-command-gate.sh`](.codex/hooks/agent-command-gate.sh)。既知の限界は Issue #129。

#### 4. issue-start-gate

- **概要**: Issue dispatch 前に blocker evidence（waiver 含む）を検査し、未解消なら起動を拒否する。
- **スコープ**: Task（Claude）／spawn_agent（Codex）。
- **PF 間差異**: matcher がディスパッチ機構名に合わせて異なる。
- **実装構成**: [`.claude/hooks/issue-start-gate.sh`](.claude/hooks/issue-start-gate.sh)、[`.codex/hooks/issue-start-gate.sh`](.codex/hooks/issue-start-gate.sh)

#### 6. check-governance-drift

- **概要**: 正本集合（`CLAUDE.md`＋`.claude/rules/*.md`＋`.ai/guidance/common.md`）の連結ハッシュと `governance-directives.md` の marker を突き合わせ、乖離があれば warning を出す（fail-open nag）。
- **スコープ**: Write／Edit 後。Claude 専用。
- **実装構成**: [`.claude/hooks/check-governance-drift.sh`](.claude/hooks/check-governance-drift.sh)

#### 7. subagent-karte-inject

- **概要**: `issue-fixer` 起動時にカルテ（`tmp/_karte/`）の診断コンテキストを注入する。
- **スコープ**: SubagentStart（issue-fixer）。Claude 専用。
- **実装構成**: [`.claude/hooks/subagent-karte-inject.sh`](.claude/hooks/subagent-karte-inject.sh)

#### 8. subagent-worktree-bind

- **概要**: `issue-implementer`／`issue-fixer` 起動時に linked worktree を割り当てる。
- **スコープ**: SubagentStart。Claude 専用（Codex は worktree bind 非採用）。
- **実装構成**: [`.claude/hooks/subagent-worktree-bind.sh`](.claude/hooks/subagent-worktree-bind.sh)

#### 9. subagent-stop-gate

- **概要**: `issue-implementer`／`issue-fixer` 停止時に worktree の後処理を行う。
- **スコープ**: SubagentStop。Claude 専用。
- **実装構成**: [`.claude/hooks/subagent-stop-gate.sh`](.claude/hooks/subagent-stop-gate.sh)

#### 10. on-rate-limit（Claude）／ 11. codex-rate-limit-stop-hook（Codex）

- **概要**: レートリミット検知時の自動復帰。Claude は StopFailure(rate_limit) で発火し、WSL＋tmux 環境でのみ `resume-watcher.sh` を setsid で起動する（クラウドでは no-op）。Codex は Stop hook で同等の検知を行う。
- **PF 間差異**: ライフサイクルイベント名と復帰機構が異なる。Claude は `on-rate-limit.sh`→`resume-watcher.sh`（`lib-pane-guard.sh` を共有ライブラリとして source）。Codex は `codex-rate-limit-stop-hook.sh`（補助: `codex-rate-limit-watcher.sh`、`codex-with-rate-limit-recovery.sh`）。
- **実装構成**: [`.claude/hooks/README.md`](.claude/hooks/README.md)、[`.codex/hooks/README.md`](.codex/hooks/README.md)

#### 12. inject-governance

- **概要**: 毎ターン、正本（`CLAUDE.md`＋`.claude/rules/*.md`）の中核規範を `governance-directives.md` 経由で注入する。
- **スコープ**: UserPromptSubmit（全 matcher）。Claude 専用。
- **実装構成**: [`.claude/hooks/inject-governance.sh`](.claude/hooks/inject-governance.sh)

#### 13. install_pkgs

- **概要**: セッション開始・再開時に必要パッケージをインストールする。
- **スコープ**: SessionStart（startup／resume）。Claude 専用。
- **実装構成**: [`.claude/hooks/install_pkgs/install_pkgs.sh`](.claude/hooks/install_pkgs/install_pkgs.sh)

#### 14. orchestrator-context

- **概要**: セッション開始時に主文脈（orchestrator）のコンテキストを設定する。
- **スコープ**: SessionStart（startup／clear／compact）。Claude 専用。
- **実装構成**: [`.claude/hooks/orchestrator-context.sh`](.claude/hooks/orchestrator-context.sh)

### 補助スクリプト（hook 呼び出し実体ではないもの）

以下は hook から呼ばれる共有ライブラリ・外部起動スクリプトであり、ライフサイクル hook の呼び出し実体ではない。

| スクリプト | PF | 用途 |
|---|---|---|
| `.claude/hooks/lib-pane-guard.sh` | Claude | `on-rate-limit.sh`／`resume-watcher.sh` が source する共有ライブラリ（状態パス・ペイン判定・tmux ラッパ） |
| `.claude/hooks/resume-watcher.sh` | Claude | `on-rate-limit.sh` から setsid で起動される復帰 watcher |
| `.codex/hooks/codex-rate-limit-watcher.sh` | Codex | Codex 版の復帰 watcher（tmux pane 監視） |
| `.codex/hooks/codex-rate-limit-query.py` | Codex | `codex-rate-limit-stop-hook.sh` の rate-limit API 問い合わせに使う補助スクリプト |
| `.codex/hooks/codex-with-rate-limit-recovery.sh` | Codex | レートリミット復帰付きで Codex CLI を起動するラッパ |

## 常駐入口と rationale の SoT

rules、hooks の共通化・移行は対象外とする。PF の hook/dispatch/worktree/model/tools 差分は、各 PF wrapper・設定・hook の実物または `.ai/guidance/platforms/` の PF 固有原稿に残す。常駐入口は Claude が公式 `@` import、Codex／Copilot が追跡対象の生成物という loader 差分を維持する。

設計経緯・却下案・既知の制約（rationale）の SoT は `.ai/rationale/<name>.md`、索引と分離規則の SoT は `.ai/rationale/README.md`。PF 個別リストは差分の索引であり、rationale の複製先ではない。
