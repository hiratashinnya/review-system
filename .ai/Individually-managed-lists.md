# PF 個別管理リスト

共通本文の一覧は載せず、PF（Claude Code／Codex CLI／GitHub Copilot／Repo-skill）の loader・wrapper・実行メタデータに生じる差分だけを記録する。共通本文の SoT は `.ai/README.md` の配置規則に従う。

Issue #538 で退役した Codex 起動用 hook の行（旧 行12）と概要は [退役記録](rationale/codex-supervisor-retirement-538.md) へ移設した。

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
| GitHub Copilot | [.ai/model-policy.json](model-policy.json) の `platforms.copilot` と `copilot_agents` を参照する。[準備手順](../model_policy/README.md) に従い同一 surface の一覧から runtime agent を生成する。追跡対象 template は起動禁止。予算は frontmatter で表現できず、低位の写像は未定義のため STOP する。 |
| Codex CLI／Repo-skill | [.ai/model-policy.json](model-policy.json) の `platforms.codex` を参照する。[解決手順](../model_policy/README.md) で一覧から対象層の具体 ID を解決し、session/config へ指定する。`.codex/agents/*.toml` は session 設定を継承して `model` や予算キーを複製しない。 |

## 個別配置・非移植

- `codex-review` は `.claude/skills/codex-review/SKILL.md` の Claude 専用。`codex exec`、ChatGPT login、Linux/WSL の session に依存するため、Codex／Copilot／Repo-skill へは配置しない。
- `agy-delegate` は Claude では `.claude/skills/agy-delegate/SKILL.md` から `.claude/agents/agy-delegate.md` へ委譲し、具体的な MCP tool metadata と Claude 固有の返却手段を持つ。Codex では `.agents/skills/agy-delegate/SKILL.md` から `.codex/agents/agy-delegate.toml` へ委譲し、利用可能な agy MCP 能力を session で解決する。ローカル CLI／Windows Credential Manager に依存するため Copilot へは移植しない。
- `gh-create-issue` は Claude と Repo-skill（`.agents/skills/gh-create-issue/SKILL.md`）に実在する。Copilot 版は作らない。GitHub 変更の明示依頼境界と loader/tool 差分を対象 PF 限定で管理する。Claude では skill は委譲の入口だけで、実行主体は Claude 専用の `.claude/agents/gh-create-issue.md`（サブエージェント・Issue #632）。Codex の `.agents/skills/` は従来どおり共通本文を直接実行し、Codex／Copilot にエージェント版は作らない。
- `silent-failure-diagnosis` は Claude（`.claude/skills/silent-failure-diagnosis/SKILL.md`・`user-invocable: false`）と Repo-skill（`.agents/skills/silent-failure-diagnosis/SKILL.md`・`user-invocable` なし）に実在する。Copilot へは配置せず（オーナー再確定 2026-10-12）、`copilot-instructions.md` へも本文を展開しない。非移植であることは `.ai/guidance/platforms/copilot.md`「Copilot 固有の非移植」にも名前で記録する（名前の記載は展開に当たらない）。`asset_parity` では、未展開の `user-invocable: false` skill は Instructions へ展開すべきもので skill/prompt にしないため、`.github/skills/<name>/SKILL.md` を置いても `present` と扱われず、`asset_parity/exceptions.py` の登録で `exempt` にしている（登録が無ければ `MISSING`）。この登録は Copilot から参照できることの根拠ではない。
- `issue-fixer`／`issue-implementer`／`pr-reviewer` は Claude と Codex に実在する。Copilot Agent 版は非移植。Claude hook、Task、gh CLI、`karte`、ロール別 push／merge 境界を Copilot で同一契約にできないため。

## 追加 wrapper

`doc-system-config-operator` は共通本文を各 loader 形式へ変換した wrapper を追加している。

- Claude: `.claude/agents/doc-system-config-operator.md`（`tools`／`model`／`skills`）
- Codex: `.codex/agents/doc-system-config-operator.toml`（`name`／`description`／`developer_instructions`）
- Copilot: `.github/agents/doc-system-config-operator.agent.md`（`model`／`tools`）

関連手順の `doc-system-config` skill は Codex の repo-skill 入口 `.agents/skills/doc-system-config/SKILL.md` にのみ配置する。共通 Agent 本文はこの Codex 固定 path を参照せず、Claude／Codex／Copilot の各 wrapper 入口を維持する。Claude／Copilot に同名 skill を複製しない。

## PF 固有の実行差分

- Claude は Task/Agent dispatch、`isolation: "worktree"`、`issue-start-gate.sh` 等の hook、ロール別 command gate を持つ。
- Codex は `spawn_agent` と `.codex/hooks.json` を持ち、そこに登録した PreToolUse hook（`agent-command-gate.sh`・`issue-start-gate.sh`。下記「ライフサイクル hook 一覧」の行 1・3）を使う。Claude の worktree bind/stop hook は配置しない。
- Claude の `issue-implementer`／`issue-fixer` だけが、`python3 -m codex_worktree_exec` で自分の linked worktree に Codex を実行者として起動できる（Issue #538 PR-B・契約は `docs/methods/codex-workspace-binding.md`）。Codex／Copilot にこの起動経路は無い。Codex は起動される側で、権限境界は `.codex/config.toml` の permission profile が担い、Codex 用 hook は追加しない。
- Copilot は Prompt の明示起動と Agent の選択・委譲を使う。Claude/Codex 相当の project hook、PreToolUse、worktree bind は配置しない。

## Hook 構成一覧

### ライフサイクル hook 一覧（PF 別適用有無）

| # | ライフサイクル hook | 呼び出し実体 | Claude Code | Codex CLI | Copilot |
|---|---|---|:---:|:---:|:---:|
| 1 | PreToolUse（Bash） | `agent-command-gate.sh` | ✅ | ✅ | — |
| 2 | PreToolUse（ctx_execute 系） | `agent-command-gate.sh` | ✅ | — | — |
| 3 | PreToolUse（Task／spawn_agent） | `issue-start-gate.sh` | ✅ | ✅ | — |
| 4 | PostToolUse（Write／Edit） | `check-governance-drift.sh` | ✅ | — | — |
| 5 | SubagentStart（issue-fixer） | `subagent-karte-inject.sh` | ✅ | — | — |
| 6 | SubagentStart（implementer／fixer） | `subagent-worktree-bind.sh` | ✅ | — | — |
| 7 | SubagentStop（implementer／fixer） | `subagent-stop-gate.sh` | ✅ | — | — |
| 8 | StopFailure（rate_limit） | `on-rate-limit.sh` | ✅ | — | — |
| 9 | UserPromptSubmit | `inject-governance.sh` | ✅ | — | — |
| 10 | SessionStart（startup／resume） | `install_pkgs.sh` | ✅ | — | — |
| 11 | SessionStart（startup／clear／compact） | `orchestrator-context.sh` | ✅ | — | — |
| 12 | SubagentStop（gh-create-issue） | `subagent-draft-display.sh` | ✅ | — | — |

> Copilot はリポジトリ固有のライフサイクル hook に非対応（`.ai/guidance/platforms/copilot.md` で確認済み）。
>
> Codex 実行者経路（`codex_worktree_exec`・Issue #538 PR-B）は hook ではなく、そのための Codex 用 hook も追加していない。権限境界は permission profile（`.codex/config.toml`）、execpolicy（`.codex/rules/default.rules`）、Claude 側の行 1・2 が担う。

### 各 hook の概要

#### Merge 権限（native direct-prefix rules と共有 command hooks）

- **概要**: AI ロールと主文脈は merge／auto-merge を実行しない。Claude の permission rules と Codex の execpolicy は直接形の command prefix を拒否し、両 `agent-command-gate` hook は全ロールに共有 merge 判定を適用する。実際の merge はオーナーが fresh blocker report を確認した後に手動で行う。
- **責務分担**: Native rules は直接形の prefix を扱う。両 hook は global option、wrapper、API、検査可能な間接実行形式を含む shell command の merge 判定を担う。読み取り形式は許可する。Codex native rule の前置 repository flag による非 merge command の拒否や、merge hook の非担当という例外はない。
- **範囲と限界**: Hook は OS sandbox ではなく静的 command-text 検査である。Git alias、shell function、別 executable、script 内の実行は保証しない。Claude の live permission engine と製品セッションの role dispatch は未測定。対応形と限界は [`docs/tools/pr-merge-gate.md`](../docs/tools/pr-merge-gate.md) を参照。
- **実装構成**: `.claude/settings.json`／`.codex/rules/default.rules`、`.claude/hooks/agent-command-gate.sh`／`.codex/hooks/agent-command-gate.sh`。

#### 1–2. agent-command-gate

- **概要**: ロール別（`issue-implementer`／`issue-fixer`／`pr-reviewer`）に push 等の操作を制限し、全ロールに共有 merge 判定を適用する。ctx_execute 系 MCP ツールにも適用する。
- **スコープ**: Bash、context-mode 実行系ツール。
- **PF 間差異**: Claude は Bash＋ctx_execute 系の2 matcher。Codex は Bash のみ（ctx_execute 系は Codex に未導入）。Claude 版だけが `issue-implementer`／`issue-fixer` に `python3 -m codex_worktree_exec`（`--role` が自ロールと一致する形のみ）を許可し、Codex 版には入れない（Codex の中からの再帰起動は `.codex/rules/default.rules` とラッパー自身が拒否する・Issue #538 D6）。2ツリーは共通化しておらず内容が乖離している（PR-B 着手時点で `.claude/` 約78.7K／`.codex/` 約70K。共通化は Issue #538 の範囲外）。
- **実装構成**: [`.claude/hooks/agent-command-gate.sh`](../.claude/hooks/agent-command-gate.sh)、[`.codex/hooks/agent-command-gate.sh`](../.codex/hooks/agent-command-gate.sh)（`.codex/hooks/README.md` の「PreToolUse command gate」節にも概要あり）。既知の限界は Issue #129。

#### 3. issue-start-gate

- **概要**: Issue dispatch 前に blocker evidence（waiver 含む）を検査し、未解消なら起動を拒否する（managed dispatch のみ）。加えて、これとは独立した安全機構として、残留 worktree があれば managed／unmanaged を問わず**全 dispatch を fail-close で deny する**（Issue #354）。自動解放が失敗した場合やフックが発火しなかった場合の最後の砦として機能する。
- **スコープ**: Task／runtime Agent（Claude）／spawn_agent（Codex）。
- **PF 間差異**: 判定ロジックは PF 非依存の共有 Python パッケージ `issue_start`（`python3 -m issue_start.hook`）に一本化されている。`.claude/hooks/issue-start-gate.sh`／`.codex/hooks/issue-start-gate.sh` は起動するだけの薄いラッパースクリプト。差異は matcher と dispatch の扱い。Claude は `Task`/`Agent` を対象に、dispatch prompt の marker `ISSUE_START_BINDING_V1` を binding 材料として検査する。Codex は `spawn_agent` を対象にするが binding 材料を持たず、既知の `issue-implementer`／`issue-fixer` を指定した dispatch を、payload の詳細・marker・ledger・cwd・GitHub API を読む前に常時 `ISSUE_START_TRANSPORT_UNAVAILABLE` で deny する（Codex は主文脈にしない＝Issue #538）。
- **実装構成**: [`docs/tools/issue-start-and-branch-source.md`](../docs/tools/issue-start-and-branch-source.md)（`.claude/hooks/issue-start-gate.sh`／`.codex/hooks/issue-start-gate.sh` はこの共有 core への薄いラッパー。`.claude/hooks/README.md`／`.codex/hooks/README.md` はこの hook の blocker 判定部分を扱っていない）。残留 worktree deny の詳細は [`.claude/hooks/README.md`](../.claude/hooks/README.md)（「残留 worktree での次 dispatch を deny する」節）

#### 4. check-governance-drift

- **概要**: 正本集合（`CLAUDE.md`＋`.claude/rules/*.md`＋`.ai/guidance/common.md`）の連結ハッシュと `governance-directives.md` の marker を突き合わせ、乖離があれば warning を出す（fail-open nag）。
- **スコープ**: Write／Edit 後。Claude 専用。
- **実装構成**: [`.claude/hooks/check-governance-drift.sh`](../.claude/hooks/check-governance-drift.sh)（`.claude/hooks/README.md` の「規範の追従漏れ検知フック」節）

#### 5. subagent-karte-inject

- **概要**: `issue-fixer` 起動時にカルテ（`tmp/_karte/`）の診断コンテキストを注入する。
- **スコープ**: SubagentStart（issue-fixer）。Claude 専用。
- **実装構成**: [`.claude/hooks/subagent-karte-inject.sh`](../.claude/hooks/subagent-karte-inject.sh)（`.claude/hooks/README.md` の「subagent ライフサイクルフック」節）

#### 6. subagent-worktree-bind

- **概要**: `issue-implementer`／`issue-fixer` 起動時に linked worktree を割り当てる。
- **スコープ**: SubagentStart。Claude 専用（Codex は worktree bind 非採用）。
- **実装構成**: [`.claude/hooks/subagent-worktree-bind.sh`](../.claude/hooks/subagent-worktree-bind.sh)（`.claude/hooks/README.md` の「subagent ライフサイクルフック」節）

#### 7. subagent-stop-gate

- **概要**: `issue-implementer`／`issue-fixer` 停止時に worktree の後処理を行う。
- **スコープ**: SubagentStop。Claude 専用。
- **実装構成**: [`.claude/hooks/subagent-stop-gate.sh`](../.claude/hooks/subagent-stop-gate.sh)（`.claude/hooks/README.md` の「subagent ライフサイクルフック」節）

#### 8. on-rate-limit（Claude）

- **概要**: レートリミット検知時の自動復帰。Claude は StopFailure(rate_limit) で発火し、WSL＋tmux 環境でのみ `resume-watcher.sh` を setsid で起動する（クラウドでは no-op）。Codex 側の自動復帰機構は撤去済み（Codex は `codex exec` のサブ実行者であり、レートリミット時は同じモデル・同じ構成で再投入する。Issue #569）。
- **PF 間差異**: Claude のみ。`on-rate-limit.sh`→`resume-watcher.sh`（`lib-pane-guard.sh` を共有ライブラリとして source）。
- **実装構成**: [`.claude/hooks/README.md`](../.claude/hooks/README.md)（「レートリミット自動再開フック」節）

#### 9. inject-governance

- **概要**: 毎ターン、正本（`CLAUDE.md`＋`.claude/rules/*.md`）の中核規範を `governance-directives.md` 経由で注入する。
- **スコープ**: UserPromptSubmit（全 matcher）。Claude 専用。
- **実装構成**: [`.claude/hooks/inject-governance.sh`](../.claude/hooks/inject-governance.sh)（`.claude/hooks/README.md` の「規約注入フック」節）

#### 10. install_pkgs

- **概要**: セッション開始・再開時に必要パッケージをインストールする。
- **スコープ**: SessionStart（startup／resume）。Claude 専用。
- **実装構成**: [`.claude/hooks/install_pkgs/install_pkgs.sh`](../.claude/hooks/install_pkgs/install_pkgs.sh)

#### 11. orchestrator-context

- **概要**: セッション開始時に主文脈（orchestrator）のコンテキストを設定する。
- **スコープ**: SessionStart（startup／clear／compact）。Claude 専用。
- **実装構成**: [`.claude/hooks/orchestrator-context.sh`](../.claude/hooks/orchestrator-context.sh)（`.claude/hooks/README.md` の「オーケストレータ委譲ルール注入フック」節）

### 補助スクリプト（hook 呼び出し実体ではないもの）

以下は hook から呼ばれる共有ライブラリ・外部起動スクリプトであり、ライフサイクル hook の呼び出し実体ではない。

| スクリプト | PF | 用途 |
|---|---|---|
| `.claude/hooks/lib-pane-guard.sh` | Claude | `on-rate-limit.sh`／`resume-watcher.sh` が source する共有ライブラリ（状態パス・ペイン判定・tmux ラッパ） |
| `.claude/hooks/resume-watcher.sh` | Claude | `on-rate-limit.sh` から setsid で起動される復帰 watcher |

## 常駐入口と rationale の SoT

rules、hooks の共通化・移行は対象外とする。PF の hook/dispatch/worktree/model/tools 差分は、各 PF wrapper・設定・hook の実物または `.ai/guidance/platforms/` の PF 固有原稿に残す。常駐入口は Claude が公式 `@` import、Codex／Copilot が追跡対象の生成物という loader 差分を維持する。

設計経緯・却下案・既知の制約（rationale）の SoT は `.ai/rationale/<name>.md`、索引と分離規則の SoT は `.ai/rationale/README.md`。PF 個別リストは差分の索引であり、rationale の複製先ではない。
