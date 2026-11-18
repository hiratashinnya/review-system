# Issue #858「[Tracking / Simplification] Claude Code標準worktreeを活用し、worktree所有台帳とgitgateの重複制御を縮小・撤去する」

- 取得時状態: open
- 評価: P1 / 新設・整合調整
- URL: https://github.com/hiratashinnya/review-system/issues/858
- 本文・ACの逐件メモ: ../memos/issue-0858.md

## 根拠と時点の整理

既存のworktree所有台帳/独自gitgateを標準worktreeへ置換する新方針。#745のI-01〜I-05（#752〜#756）が同じモジュールを責務分割する計画と重なる。

## 推奨処置

#859の実測・オーナー方針確定まではI系の独立リファクタを無調整で進めない。#559/#662/#855との役割分担を確定する。

## 注意

本文内の歴史的スナップショットを自動改変・消去しない。実装が必要な箇所は現行mainで再現し、ACは証拠無しに合格と判定しない。今回の棚卸しでIssue本文・PR・コードは変更していない。
