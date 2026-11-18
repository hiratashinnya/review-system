# Issue #756「[Maintainability I-05] durable_lockとSessionStartの小規模負債を解消」

- 取得時状態: open
- 評価: P2 / スコープ競合可能性
- URL: https://github.com/hiratashinnya/review-system/issues/756
- 本文・ACの逐件メモ: ../memos/issue-0756.md

## 根拠と時点の整理

durable_lock/SessionStart等を分割する計画は、#858での台帳・lockの存続判断と重なる可能性。

## 推奨処置

存続するlock責務と単独残す機能を特定してから着手。

## 注意

本文内の歴史的スナップショットを自動改変・消去しない。実装が必要な箇所は現行mainで再現し、ACは証拠無しに合格と判定しない。今回の棚卸しでIssue本文・PR・コードは変更していない。
