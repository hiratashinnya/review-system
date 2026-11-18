# Issue #805「docs(karte): model.py 入口の docstring 要約化後、同「改ざん防止の機械的裏付けと既知の限界」節を名指す4文書の参照先を rationale へ更新する（F-799-07）」

- 取得時状態: open
- 評価: P1 / 確認済
- URL: https://github.com/hiratashinnya/review-system/issues/805
- 本文・ACの逐件メモ: ../memos/issue-0805.md

## 根拠と時点の整理

PR #799 は2026-11-11にmerged。mainのkarte/model.pyは79行で詳細の所在を.ai/rationale/karte-module-split.mdに移設済み。現行文書の一部は旧docstringの詳細を探す。

## 推奨処置

現行説明の参照先を入口＋rationaleに更新。governance-directivesの過去の編集履歴コメントは歴史的証拠として保持し、機械的に一律書換しない。

## 注意

本文内の歴史的スナップショットを自動改変・消去しない。実装が必要な箇所は現行mainで再現し、ACは証拠無しに合格と判定しない。今回の棚卸しでIssue本文・PR・コードは変更していない。
