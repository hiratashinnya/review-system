# Issue #285「CLAUDE.md の codex-review 要約を正本の安全な実行契約へ同期する」

- 取得時状態: open
- 評価: P2 / 再評価要
- URL: https://github.com/hiratashinnya/review-system/issues/285
- 本文・ACの逐件メモ: ../memos/issue-0285.md

## 根拠と時点の整理

旧 PR #260 のcodex-review安全要約同期が対象だが PR #260 はclosed / unmerged。#605/#575の再実装範囲からcodex-review固有契約は明示的に外されている。

## 推奨処置

現行のcodex-review実行入口と正本を再読し、未移管の防御規定だけを移管。無条件クローズはしない。

## 注意

本文内の歴史的スナップショットを自動改変・消去しない。実装が必要な箇所は現行mainで再現し、ACは証拠無しに合格と判定しない。今回の棚卸しでIssue本文・PR・コードは変更していない。
