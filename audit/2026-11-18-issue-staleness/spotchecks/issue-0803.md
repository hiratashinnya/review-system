# Issue #803「[#375 子4] pr-reviewer の権限分離を機械で強制する（PR コメント投稿経路・worktree 隔離・Write パス制限の hook 依存）」

- 取得時状態: open
- 評価: P2 / 確認済
- URL: https://github.com/hiratashinnya/review-system/issues/803
- 本文・ACの逐件メモ: ../memos/issue-0803.md

## 根拠と時点の整理

前提 PR #697・子 #800 は統合済み/closed。本文に未マージstackを前提とする表現が残る。権限分離の強制自体は別課題として有効。

## 推奨処置

現行main基準でWrite制限・PR投稿・hook停止時の境界を検証。実装前提のみ更新。

## 注意

本文内の歴史的スナップショットを自動改変・消去しない。実装が必要な箇所は現行mainで再現し、ACは証拠無しに合格と判定しない。今回の棚卸しでIssue本文・PR・コードは変更していない。
