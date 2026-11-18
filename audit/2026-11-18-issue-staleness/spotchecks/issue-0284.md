# Issue #284「agy-mcp-bridge のローカルパッチを更新・再 clone 後も安全に維持する」

- 取得時状態: open
- 評価: P1 / 条件付き陳腐化
- URL: https://github.com/hiratashinnya/review-system/issues/284
- 本文・ACの逐件メモ: ../memos/issue-0284.md

## 根拠と時点の整理

Issue目的は外部 agy-mcp-bridge のpatchを維持すること。#575でbridge撤去へ方針転換したが、#607のユーザー環境での撤去は未実施。

## 推奨処置

#607の撤去を正規に実測するまで安全対策を勝手に解除しない。撤去後にパッチ維持要件の不要化を根拠付きで決定する。

## 注意

本文内の歴史的スナップショットを自動改変・消去しない。実装が必要な箇所は現行mainで再現し、ACは証拠無しに合格と判定しない。今回の棚卸しでIssue本文・PR・コードは変更していない。
