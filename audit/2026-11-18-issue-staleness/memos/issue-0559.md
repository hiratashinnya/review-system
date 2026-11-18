# Issue #559「worktree残留がgitgate/issue-start-gateで解消されず主文脈の手作業が必要になる（Issue #502同一症状の再発・3経路）」

- URL: https://github.com/hiratashinnya/review-system/issues/559
- 状態: open（2026-11-18取得）
- 本文: 6916文字/ 171行。全文: `../raw/issues-2026-09.jsonl`
- AC: 7件（未チェック: 7）
- Issue参照: #502, #535, #555, #558, #409, #615, #605, #733, #699, #679, #745, #757, #761
- PR参照: #555, #558, #615, #733
- 主見出し: ## 目的・背景 | ## 現状と根拠（実測・2026-09-27〜28） | ### 1回目：台帳に紐づかない worktree（issue-implementer round1・Issue #535/PR #555 向け） | ### 2回目：回収済みなのに実体が残留（issue-fixer round1・PR #555 是正） | ### 3回目：台帳が `running`・実際は非稼働（issue-fixer round4・PR #558 是正） | ## 影響 | ## Scope | ## Out of scope | ## 再現手順・期待結果・実際結果・環境・root cause 仮説 | ## Acceptance criteria | ## Dependencies / Related issues | ## 追記（2026-10-12・オーナー判断・Claude Code (AI) が実施）
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- ## 現状と根拠（実測・2026-09-27〜28）
- - Related: #409（AgentRun ledger と close gate による実行ライフサイクルの機械管理・OPEN。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
