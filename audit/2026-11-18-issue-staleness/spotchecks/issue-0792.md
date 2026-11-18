# Issue #792「[重複実装の統合] karte ingest の owner scope 適用・karte_notify の shell 解析・review envelope 語彙を1箇所へ（#375 / PR #697 レビュー由来）」

- 取得時状態: open
- 評価: P2 / 確認済
- URL: https://github.com/hiratashinnya/review-system/issues/792
- 本文・ACの逐件メモ: ../memos/issue-0792.md

## 根拠と時点の整理

対象コードはPR #697/#696のmain統合待ちと記すが両PRはmerged。実装の重複3件が現存するかは別確認が必要。

## 推奨処置

最新mainで重複箇所と#751、#785の実装範囲を再点検して小さな独立修正へ。

## 注意

本文内の歴史的スナップショットを自動改変・消去しない。実装が必要な箇所は現行mainで再現し、ACは証拠無しに合格と判定しない。今回の棚卸しでIssue本文・PR・コードは変更していない。
