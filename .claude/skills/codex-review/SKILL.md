---
name: codex-review
description: ユーザーが明示起動する「Codex 公式 CLI (`codex exec`) への第二意見レビュー委譲」の入口。別モデルファミリ（OpenAI）へ read-only の PR・実装・設計レビューを依頼するときに使う。agy MCP bridge や in-repo の Claude レビュー→merge には使わない。
disable-model-invocation: true
---

# Codex 公式 CLI への第二意見レビュー委譲

**別モデルファミリ（OpenAI）の視点**で、PR・実装・設計に敵対的/セキュリティレビューを回すための**Claude Code 専用・ユーザー起動の入口**。設計背景と非移植理由は [codex-review の rationale](../../../.ai/rationale/codex-review.md) に置く。

> 使い分け：**agy MCP bridge (`mcp__agy__codex_*`) は使わない**（agy 経由の委譲は `agy-delegate`）。
> **in-repo の Claude 自身によるレビュー→コメント→merge は `pr-reviewer`**。本スキルは「別ファミリの第二意見を取りに行く」専用。

## 呼び方（標準手順）

1. 観点プロンプトをファイルに書く（`tmp/` 等）。cwd をリポジトリにして、未コミット diff / 対象ファイルを Codex に読ませる。
2. 非対話で実行：
   ```bash
   codex exec -m <model> --sandbox read-only - < prompt.txt > review.txt 2>&1
   ```
   - stdin に観点プロンプトを流す（`-` が stdin 指定）。`--sandbox read-only` で書き込みをさせない。
   - `model` は**オーナー指定**（例 `gpt-5.6`）。`codex exec review` サブコマンドもある。
3. `review.txt`（最終応答）を読む。flag や環境エラーがあれば troubleshooting の回復手順へ進む。

cyber フィルタ、rollout 回収、CLI／認証の環境制約に遭遇した場合は [codex-review の troubleshooting](../../../.ai/troubleshooting/codex-review.md) の回復手順に従う。

## done 条件

- [ ] 観点プロンプトを防御形式で書き、`codex exec -m <model> --sandbox read-only` で流した。
- [ ] `review.txt` の末尾を確認。ERROR(flagged) なら troubleshooting の回復手順を実施した。
- [ ] 所見を Claude 側レビューと統合し、**AI（Codex 由来）であることを明示して**オーナー/PR へ報告した（独断で「対応不要」としない＝CLAUDE.md）。
