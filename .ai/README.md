# `.ai/` 共通資産

Issue #406 の移行方針では、`.ai/` を PF（プラットフォーム）に依存しない共通本文の Source of Truth（SoT）とする。各 PF の実行場所には、ローダーが要求する frontmatter/TOML、ツール・モデル・権限設定、起動方式、PF 固有の運用契約だけを wrapper/metadata として残す。共通本文を PF ごとに複製しない。

## 共通資産の配置

| 種別 | SoT |
|---|---|
| Skill | `.ai/skills/<name>/SKILL.md` |
| Agent | `.ai/agents/<name>.md` |
| 設計経緯・却下案・既知の制約 | `.ai/rationale/<name>.md` |
| rationale の索引・分離規則 | `.ai/rationale/README.md` |
| リポジトリ共通の常駐 guidance | `.ai/guidance/common.md` |

PF wrapper は共通本文への相対リンクを持つ。PF 差分は実行契約の一部なので wrapper/metadata 側に残すが、共通本文の正本にはしない。[Individually-managed-lists.md](Individually-managed-lists.md) は、実在ファイルと未配置を含む PF 個別差分専用の管理リストである。

## Issue #406 の推奨スコープ

対象は次の4つの PF tree である。`.ai/` 自体は共通 SoT であり、PF tree には数えない。

| PF tree | 実行・探索入口 | wrapper/metadata の役割 |
|---|---|---|
| Claude | `.claude/skills/`、`.claude/agents/` | Claude frontmatter、tools/model/effort、hook・dispatch 固有契約 |
| Codex | `.codex/agents/` | Codex custom-agent TOML。repo skill の探索入口は `.agents/skills/` |
| GitHub Copilot | `.github/skills/`、`.github/prompts/`、`.github/agents/`、`.github/copilot-instructions.md` | Skill/Prompt/Agent/Instructions の起動方式と Copilot metadata |
| Review-system repo skills | `.agents/skills/` | リポジトリ内 Skill の探索用 wrapper と metadata |

既存の rules、Claude hooks、PF 固有実行機構は `.ai/` へ移行しない。常駐入口だけは次の方式で共通 guidance に接続する。

- Claude: `CLAUDE.md` の公式 `@.ai/guidance/common.md` import。生成・生成物同期検査の対象外。
- Codex／Copilot: `.ai/guidance/common.md` と `.ai/guidance/platforms/*.md` から `python3 -m guidance_sync render` で `AGENTS.md`／`.github/copilot-instructions.md` を生成する。生成物は追跡し、先頭 marker に生成元と各 SHA-256 を記録する。
- 仕様原則: `.ai/skills/spec-principles/SKILL.md` が PR1–PR10 の正本で、common の原則節は常駐 guidance 用の意味保存写しである。common と生成物は正本 hash を marker に持ち、正本だけを変更して写しを更新しない drift を検知する。
- 検査: `python3 -m guidance_sync check` は working tree、`python3 -m guidance_sync staged-check` は staged index を検査する。後者は自動生成・自動 stage を行わず、spec-principles を変更した場合は common と両生成物の明示 stage も要求する。

導入手順と pre-commit hook は [`.githooks/README.md`](../.githooks/README.md) を参照する。
