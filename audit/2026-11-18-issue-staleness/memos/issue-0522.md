# Issue #522「feedback_ledger: TOML スキーマ3種と機械 lint（canonical/immutability）を実装する」

- URL: https://github.com/hiratashinnya/review-system/issues/522
- 状態: closed（2026-11-18取得）
- 本文: 7059文字/ 110行。全文: `../raw/issues-2026-09.jsonl`
- AC: 9件（未チェック: 9）
- Issue参照: #513, #512, #310, #330
- PR参照: なし
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## Scope | ### 文書スキーマ3種（TOML） | ### lint 規則（`check`） | ### CLI verb | ### 周辺 | ## Out of scope | ## Acceptance criteria | ## 利用者価値 | ## 提案挙動 | ## 互換性
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- `new-entry --from <draft.toml>` / `propose --from` / `amend-proposal --from` / `approve --triage <TRG-id> --by <who>` / `reject --proposal <id> --by <who> --reason <text>` / `apply-done` / `triage-open` / `triage-close` / `check [
- - 終了コードは `dsv2` / `karte` に合わせる（`0` OK ／ `2` 未検出 ／ `4` 前提違反・検証失敗）。
- 2. `python3 -m feedback_ledger new-entry --from <draft>` が検証・正規化して `.ai/feedback/ledger/` へ書く。違反があれば取り込みごと拒否する（fail-close）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
