# `.ai/schema/` — 共通 schema の正本（非活性）

ここには PF に依存しない AI 資産の機械可読な契約を置く。現在の配置契約は
[`asset-placement-v1.json`](asset-placement-v1.json) である。

## 配置規律

| 種別 | 正本 | 説明 |
|---|---|---|
| 規範 | `.ai/skills/<name>/SKILL.md`、`.ai/agents/<name>.md` | 実行時に必要な責務・I/F・停止条件 |
| ADR／rationale | `.ai/rationale/<name>.md` | 設計理由、却下案、変更経緯、既知の制約 |
| troubleshooting | `.ai/troubleshooting/<asset>.md` | asset ごとの index。incident は本文見出しで分け、障害の症状、復旧手順、実測ログを記録する |
| 共有 schema | `.ai/schema/<name>-v<major>.json` | 上記資産や検証器が共有する形式契約 |

このディレクトリ自体は loader-facing asset ではない。schema を変更したときは、
それを読む検証器と回帰テストを同じ変更で更新する。PF wrapper に schema の本文を
複製せず、必要な場合はリポジトリ相対リンクで参照する。troubleshooting の
`<asset>` は schema の許可リストにある asset 名であり、incident suffix を持つ別ファイルは作らない。
