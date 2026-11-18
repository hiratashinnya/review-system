# Issue #576「PR #233 の公開前 remote 検証要件を #538／gitgate の複数ロール push 設計へ引き渡す」

- URL: https://github.com/hiratashinnya/review-system/issues/576
- 状態: open（2026-11-18取得）
- 本文: 2242文字/ 57行。全文: `../raw/issues-2026-10.jsonl`
- AC: 4件（未チェック: 4）
- Issue参照: #233, #538, #452
- PR参照: #233
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## 引き渡す要件 | ## 再利用しにくい点 | ## 未確定事項 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- PR #233（draft・2026-07-18・Codex 作）は `worktree-publish` skill と gitgate の read-only verb `publish-info` を提案していた。#233 は先に入れると #538 との順序が逆転するため close する。#233 が持っていた要件と知見を失わないよう、#538 または gitgate の複数ロール push 設計へ引き渡す。
- - #233 は現在 CONFLICTING。Codex の公開経路は host publish（#452 系）に置換済み。Codex supervisor は #538 で撤去し `codex exec -C` の薄いラッパー化する予定で、サブエージェント向けロールのフックの扱いは #538 の要設計事項。
- - 事実関係の記録: #233 の PR 本文は「指定された 3 ファイルのみを変更」と記載するが、実差分は 8 ファイル（`.agents/skills/worktree-publish/SKILL.md`・`agents/openai.yaml`・`.codex/agents/issue-implementer.toml`・`.codex/hooks/agent-command-gate.sh`・`gitgate/cli.py`・`tests/unit
- - Blocked by: なし（実装着手の前提として #538 の設計方針を参照する）

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
