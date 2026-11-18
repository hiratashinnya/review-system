# Issue #578「harness と dsv2 の既存テストコードを tests/道具名/ へ移設する」

- 取得時状態: open
- 評価: P2 / 確認済
- URL: https://github.com/hiratashinnya/review-system/issues/578
- 本文・ACの逐件メモ: ../memos/issue-0578.md

## 根拠と時点の整理

Blocker #542 と #538 はいずれもclosed。テストを tests/<tool>/ に移す計画の着手前提は満たされた。

## 推奨処置

今のtests/実ファイルを再棚卸しし、削除済みテストを対象外にした移設計画へ更新。

## 注意

本文内の歴史的スナップショットを自動改変・消去しない。実装が必要な箇所は現行mainで再現し、ACは証拠無しに合格と判定しない。今回の棚卸しでIssue本文・PR・コードは変更していない。
