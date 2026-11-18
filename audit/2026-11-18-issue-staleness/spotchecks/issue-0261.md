# Issue #261「doc_system 完了までの処置計画（2026-07-28 棚卸し）— 取りまとめ」

- 取得時状態: open
- 評価: P3 / 期限切れの基準値候補
- URL: https://github.com/hiratashinnya/review-system/issues/261
- 本文・ACの逐件メモ: ../memos/issue-0261.md

## 根拠と時点の整理

2026-07-28のdoc-system-v2ダッシュボードのopen FNDやmaterialize件数、作業ブランチを基準値として記録。4ヶ月が経過し現mainの値は未再計測。

## 推奨処置

dsv2 index/validate/drift/dashboardを再実行し、#253〜#256/#160〜#162の着手順と現在の母数を更新。履歴の数値は消さない。

## 注意

本文内の歴史的スナップショットを自動改変・消去しない。実装が必要な箇所は現行mainで再現し、ACは証拠無しに合格と判定しない。今回の棚卸しでIssue本文・PR・コードは変更していない。
