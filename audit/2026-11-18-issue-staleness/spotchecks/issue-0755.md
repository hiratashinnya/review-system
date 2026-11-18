# Issue #755「[Maintainability I-04] worktree ledger状態遷移・残留検出を分離」

- 取得時状態: open
- 評価: P2 / スコープ競合可能性
- URL: https://github.com/hiratashinnya/review-system/issues/755
- 本文・ACの逐件メモ: ../memos/issue-0755.md

## 根拠と時点の整理

worktree ledger状態遷移/残留判定の分割計画。#858では状態機械と残留ゲートを縮小対象とする。

## 推奨処置

#859の状態・実体対応を反映してACを見直す。

## 注意

本文内の歴史的スナップショットを自動改変・消去しない。実装が必要な箇所は現行mainで再現し、ACは証拠無しに合格と判定しない。今回の棚卸しでIssue本文・PR・コードは変更していない。
