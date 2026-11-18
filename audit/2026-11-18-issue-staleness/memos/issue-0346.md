# Issue #346「.claude/skills/issue-pipeline と issue-implementer.md に ISSUE_START_BINDING_V1 marker 契約の記載が無く、issue-start-gate が初回 dispatch で必ず deny する」

- URL: https://github.com/hiratashinnya/review-system/issues/346
- 状態: closed（2026-11-18取得）
- 本文: 3122文字/ 56行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 4件（未チェック: 4）
- Issue参照: #344, #345, #342
- PR参照: なし
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ### 再現 | ### 関連 Issue との違い | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - #345「issue-start gate が Claude Code on the web 環境で常に API_PERMISSION」は、binding 行自体は正しく付与できた前提で、その後の GitHub API 到達性（egress policy）が原因の別症状。本 Issue は binding 契約そのものが正本ドキュメントに存在しないという別原因・別修正。
- - Blocked by: なし

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
