# Issue #745「[Tracking / Refactor] maintainability_lint 既存負債75件を全解消する（33ファイル・領域別stack）」

- 取得時状態: open
- 評価: P1 / 確認済
- URL: https://github.com/hiratashinnya/review-system/issues/745
- 本文・ACの逐件メモ: ../memos/issue-0745.md

## 根拠と時点の整理

本文冒頭の初期負債75件・33ファイルは2026-11-06時点。現行mainのmaintainability_lint/baseline.jsonはmodule_lines 27、comment_blocks 17、mixed_class_files 0、計44件。PR #696/#697/#740/#741もすべてmergedで、本文はopenとする。

## 推奨処置

初期75件を履歴値として残し、現状44件を別節へ明記。26子Issueの完了状況・変更ファイル・今後のstack基準を更新。#858/#859とのI系重複を整理。

## 注意

本文内の歴史的スナップショットを自動改変・消去しない。実装が必要な箇所は現行mainで再現し、ACは証拠無しに合格と判定しない。今回の棚卸しでIssue本文・PR・コードは変更していない。
