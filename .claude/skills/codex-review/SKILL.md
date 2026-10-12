---
name: codex-review
description: ユーザーが明示起動する「Codex 公式 CLI (`codex exec`) への第二意見レビュー委譲」の入口。別モデルファミリ（OpenAI）へ read-only の PR・実装・設計レビューを依頼するときに使う。agy への委譲や in-repo Claude レビューには使わない。
disable-model-invocation: true
---

# Codex 公式 CLI への第二意見レビュー委譲

**別モデルファミリ（OpenAI）の視点**で、PR・実装・設計に敵対的/セキュリティレビューを回すための**Claude Code 専用・ユーザー起動の入口**。設計背景と非移植理由は [codex-review の rationale](../../../.ai/rationale/codex-review.md) に置く。

> 使い分け：**agy 直接実行への委譲は `agy-delegate`**。本スキルは Codex 公式 CLI を使う（旧 bridge 名の履歴は `.ai/rationale/agy-delegate.md`）。
> **in-repo の Claude 自身によるレビュー→コメント→merge は `pr-reviewer`**。本スキルは「別ファミリの第二意見を取りに行く」専用。

## 呼び方（標準手順）

1. 観点プロンプトを最初から防御レビュー形式でファイルに書く（`tmp/` 等）。「攻撃コマンド文字列を再現しない」「`file:line`、欠陥クラス、修正方針で返す」と指定する。cwd をリポジトリにして、未コミット diff / 対象ファイルを Codex に読ませる。
2. 非対話で実行：
   ```bash
   codex exec -m <model> --sandbox read-only - < prompt.txt > review.txt 2>&1
   ```
   - stdin に観点プロンプトを流す（`-` が stdin 指定）。`--sandbox read-only` で書き込みをさせない。
   - `model` は**オーナー指定**（例 `gpt-5.6`）。`codex exec review` サブコマンドもある。
3. `review.txt`（最終応答）を読む。flag や環境エラーがあれば troubleshooting の回復手順へ進む。flag 後は言い換え・新規セッションを問わず再提出しない（迂回に当たる）。
4. `codex exec` がレートリミットで失敗した場合は、同じモデル・同じ構成で再投入する。降格しない。

cyber フィルタ、rollout 回収、CLI／認証の環境制約に遭遇した場合は [codex-review の troubleshooting](../../../.ai/troubleshooting/codex-review.md) の回復手順に従う。

## done 条件

- [ ] 観点プロンプトを防御形式で書き、`codex exec -m <model> --sandbox read-only` で流した。
- [ ] `review.txt` の末尾を確認。ERROR(flagged) なら再提出せず、troubleshooting の回復手順（自分の `thread_id` の rollout 1ファイルからの回収、または停止報告）を実施した。
- [ ] 所見を Claude 側レビューと統合し、**AI（Codex 由来）であることを明示して**オーナー/PR へ報告した（独断で「対応不要」としない＝CLAUDE.md）。
