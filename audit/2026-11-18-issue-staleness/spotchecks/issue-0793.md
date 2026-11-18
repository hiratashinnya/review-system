# Issue #793「[書式の食い違い] binding の run_id / target_key は任意の1行を許す一方 karte review envelope は header-safe のみ受理し、該当 binding で Codex pr-reviewer が必ず失敗する（#375 / PR #697 レビュー由来）」

- 取得時状態: open
- 評価: P2 / 確認済
- URL: https://github.com/hiratashinnya/review-system/issues/793
- 本文・ACの逐件メモ: ../memos/issue-0793.md

## 根拠と時点の整理

旧PR #697/#696統合待ち記述は古い。bindingの受理集合とreview envelope header-safeの食い違いが実際に残るか未再現。

## 推奨処置

現行mainのbinding/karte両schemaを実行検証し、残存すれば最初の信頼検査で明確に拒否させる。

## 注意

本文内の歴史的スナップショットを自動改変・消去しない。実装が必要な箇所は現行mainで再現し、ACは証拠無しに合格と判定しない。今回の棚卸しでIssue本文・PR・コードは変更していない。
