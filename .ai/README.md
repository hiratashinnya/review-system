# `.ai/` 共通資産

Issue #406 の移行方針では、`.ai/` を PF（プラットフォーム）に依存しない共通本文の Source of Truth（SoT）とする。各 PF の実行場所には、ローダーが要求する frontmatter/TOML、ツール・モデル・権限設定、起動方式、PF 固有の運用契約だけを wrapper/metadata として残す。共通本文を PF ごとに複製しない。

## 共通資産の配置

| 種別 | SoT |
|---|---|
| Skill | `.ai/skills/<name>/SKILL.md` |
| Agent | `.ai/agents/<name>.md` |
| 設計経緯・却下案・既知の制約 | `.ai/rationale/<name>.md` |
| rationale の索引・分離規則 | `.ai/rationale/README.md` |

PF wrapper は共通本文への相対リンクを持つ。PF 差分は実行契約の一部なので wrapper/metadata 側に残すが、共通本文の正本にはしない。実在ファイルと未配置の対応表は [Individually-managed-lists.md](Individually-managed-lists.md) を参照する。

## Issue #406 の推奨スコープ

対象は次の4つの PF tree である。`.ai/` 自体は共通 SoT であり、PF tree には数えない。

| PF tree | 実行・探索入口 | wrapper/metadata の役割 |
|---|---|---|
| Claude | `.claude/skills/`、`.claude/agents/` | Claude frontmatter、tools/model/effort、hook・dispatch 固有契約 |
| Codex | `.codex/agents/` | Codex custom-agent TOML。repo skill の探索入口は `.agents/skills/` |
| GitHub Copilot | `.github/skills/`、`.github/prompts/`、`.github/agents/`、`.github/copilot-instructions.md` | Skill/Prompt/Agent/Instructions の起動方式と Copilot metadata |
| Review-system repo skills | `.agents/skills/` | リポジトリ内 Skill の探索用 wrapper と metadata |

rules、hooks、常時 instructions は今回 `.ai/` へ移行・変更しない。実行境界（特に hook の deny/allow）と PF の自動適用範囲は、共通本文への集約とは別の owner review 対象である。

