# Issue #5「設計⇔実装ドリフト対策：実装変更時に影響する設計書へ必ず反映する仕組みを考える」

- 取得時状態: open
- 評価: 維持 / 単純重複ではない
- URL: https://github.com/hiratashinnya/review-system/issues/5
- 本文・ACの逐件メモ: ../memos/issue-0005.md

## 根拠と時点の整理

review_system製品の設計・実装ドリフト対策。#835のharness ADR/PFD/DFD発掘は製品本体を明示的に対象外としている。

## 推奨処置

廃止/統合しない。doc-system-v2依存の現行状況だけ別途更新候補。

## 注意

本文内の歴史的スナップショットを自動改変・消去しない。実装が必要な箇所は現行mainで再現し、ACは証拠無しに合格と判定しない。今回の棚卸しでIssue本文・PR・コードは変更していない。
