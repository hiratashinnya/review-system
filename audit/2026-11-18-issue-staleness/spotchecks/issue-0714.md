# Issue #714「issue_start／karte 周りの記述がコードと食い違っている箇所を是正する（入れ子委譲・bind・GATED_ROLES・karte check）」

- 取得時状態: open
- 評価: P2 / 一部確認済
- URL: https://github.com/hiratashinnya/review-system/issues/714
- 本文・ACの逐件メモ: ../memos/issue-0714.md

## 根拠と時点の整理

現在の.ai/Individually-managed-lists.mdはSubagentStartがlinked worktreeを『割り当てる』と説明するが、issue_start/subagent_hooks.pyのrun_bindは既存dispatchのworktreeを束縛する。#614はPR #850で修正済み。

## 推奨処置

(2)の文書を実装に同期。(4)のkarte check説明は#614後のmain実装で別に再現して残否を判断。旧PR #712の未統合記述も更新。

## 注意

本文内の歴史的スナップショットを自動改変・消去しない。実装が必要な箇所は現行mainで再現し、ACは証拠無しに合格と判定しない。今回の棚卸しでIssue本文・PR・コードは変更していない。
