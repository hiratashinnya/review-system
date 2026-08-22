# PF 個別管理リスト

共通本文の一覧は載せず、PF（Claude Code／Codex CLI／GitHub Copilot／Repo-skill）の loader・wrapper・実行メタデータに生じる差分だけを記録する。共通本文の SoT は `.ai/README.md` の配置規則に従う。

## loader 差分

| PF | loader 入口 | 個別形式 |
|---|---|---|
| Claude Code | `.claude/skills/`、`.claude/agents/` | YAML frontmatter。Agent wrapper に `tools`、`model`、任意の `effort`／`skills` を置く。 |
| Codex CLI | `.agents/skills/`、`.codex/agents/` | repo-skill は Markdown、custom agent は TOML（`name`／`description`／`developer_instructions`）。Claude の frontmatter を複製しない。 |
| GitHub Copilot | `.github/skills/`、`.github/prompts/`、`.github/agents/`、`.github/copilot-instructions.md` | Skill／Prompt／Agent／Instructions の loader に分かれる。Agent は YAML frontmatter の `model`／`tools` を使う。 |
| Repo-skill | `.agents/skills/` | Codex CLI の repo-scoped skill discovery 用。Agent の配置先ではない。 |

## Bloom の model mapping

| PF | mapping |
|---|---|
| Claude Code | 軸1は Lv1→`haiku`、Lv2–3→`sonnet`。Lv4–6 は軸2で分岐し、網羅性ボトルネック→`sonnet`＋`effort: high`〜`xhigh`、判断ボトルネック→`opus`。Lv2–3 の推論予算は `effort: low`〜`medium`。 |
| GitHub Copilot | 中位モデル層→`claude-sonnet-5`、最上位モデル層→`claude-opus-4-8`。低位モデル層は live の利用可能 ID を確認できた場合だけ指定し、確認できなければ架空 ID を追加せず STOP してオーナー確認を求める。Claude の `effort` や Codex の推論予算キーは持ち込まない。 |
| Codex CLI／Repo-skill | `gpt-5.6` を固定し、低位→`model_reasoning_effort: low`、中位（小〜中）→`low`〜`medium`、中位（大〜最大）→`high`〜`xhigh`、最上位→`xhigh`。写像の適用先は Codex CLI の session/config であり、`.codex/agents/*.toml` は session 設定を継承して `model` を複製しない。 |

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

## 対象外と rationale の SoT

rules、hooks、常時 instructions の共通化・移行は今回の対象外とする。PF の hook/dispatch/worktree/model/tools 差分は、各 PF wrapper・設定・hook の実物に残す。

設計経緯・却下案・既知の制約（rationale）の SoT は `.ai/rationale/<name>.md`、索引と分離規則の SoT は `.ai/rationale/README.md`。PF 個別リストは差分の索引であり、rationale の複製先ではない。
