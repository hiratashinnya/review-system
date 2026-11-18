# Issue #583「write 権限のないロール 3 件（reconciliation-validator・dsv2-lookup・asset-auditor）の agent.md に、規範が求める artifact_policy 無効化の優先規定が無い」

- URL: https://github.com/hiratashinnya/review-system/issues/583
- 状態: closed（2026-11-18取得）
- 本文: 3970文字/ 54行。全文: `../raw/issues-2026-10.jsonl`
- AC: 4件（未チェック: 4）
- Issue参照: #565, #573, #275
- PR参照: なし
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - 関連関係は blocked-by ではなく related とする。本 Issue の修正は既存の規範（`.claude/rules/05-skills-agents.md`）を実装に合わせるものであり、#565 の案 A/B/C の選択に依存せず完了できる。#565 が案 A を採って共通規範を変更する場合に限り、優先規定の文言を整合させる。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
