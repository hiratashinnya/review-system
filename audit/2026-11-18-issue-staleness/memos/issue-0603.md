# Issue #603「Codex 主文脈前提の issue-pipeline 資産を整理する」

- URL: https://github.com/hiratashinnya/review-system/issues/603
- 状態: closed（2026-11-18取得）
- 本文: 3046文字/ 53行。全文: `../raw/issues-2026-10.jsonl`
- AC: 6件（未チェック: 0）
- Issue参照: #538, #604, #452, #468, #565
- PR参照: #604
- 主見出し: ## 目的・背景 | ## 現状と根拠（実測・2026-10-10） | ## PR #604 からの申し送り（2026-10-11・オーナー承認） | ## Scope | ## Out of scope | ## Acceptance criteria | ## 互換性 | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- Codex は主文脈にせず、Claude Code から呼ぶ実行者として使うと確定した（決定 `FBK-20260922-codexを主文脈にせずサブ扱いとする`・`audit/2026-09-21-pipeline-redesign/README.md`）。#538 が supervisor を撤去し `codex exec` の薄いラッパーへ置き換える。一方、Codex が主文脈として issue-pipeline を回す前提で作った資産は残っており、
- ## 現状と根拠（実測・2026-10-10）
- Codex 側の implementer / fixer は現在も起動できないため、退役で失われる動作中の機能は無い見込み（処置前に再確認する）。
- - Blocked by: #538（撤去と置換の完了後に着手）

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
