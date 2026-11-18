# Issue #533「`pr_merge_gate` の classifier が merge でない read-only な `gh` コマンドを deny し、実行済みコマンドに整合性エラーを出す」

- URL: https://github.com/hiratashinnya/review-system/issues/533
- 状態: closed（2026-11-18取得）
- 本文: 5590文字/ 114行。全文: `../raw/issues-2026-09.jsonl`
- AC: 5件（未チェック: 5）
- Issue参照: #553, #523, #531, #542, #428, #412, #415, #129
- PR参照: #553
- 主見出し: ## 2026-09-27 レビュー是正メモ（Codex AI agent） | ## 目的・背景 | ## 現状と根拠 | ### 観測1: `gh api` に未知のフラグが1つでも付くと `CLASSIFIER_UNKNOWN` | ### 観測2: `gh api graphql -F query=@<file>` は常に `CLASSIFIER_UNKNOWN` | ### 観測3: 実行できたコマンドの後に `POST_AUDIT_INTEGRITY_ERROR/RECLASSIFIED_NOT_MERGE` が出る | ## Scope | ## Out of scope | ## Acceptance criteria | ## 利用者価値 | ## 互換性 | ## 代替案
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- メッセージは「PreToolUse で deny されたはずの操作が PostToolUse へ到達した」と述べるが、**実測ではそのコマンドは PreToolUse を通過して正常終了している**。つまり前提の方が誤っている可能性がある。
- - Blocked by: #542（マージ権限を AI ロールから剥がし settings.json のネイティブ機構へ移す）。#542 は `pr_merge_gate/classifier.py` とその配線（`hook.py`、settings.json の `pr-merge-gate.sh` Pre／Post）を撤去する計画のため、本 Issue の残りの受け入れ条件（観測2・観測3）は #542 で解消される見込み。着手せず #542 の完了

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
