# Issue #312「test(hooks): CLAUDE.md と governance-directives.md の synced-from 同期を unittest で固定する」

- URL: https://github.com/hiratashinnya/review-system/issues/312
- 状態: closed（2026-11-18取得）
- 本文: 2036文字/ 59行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 5件（未チェック: 5）
- Issue参照: #311, #276, #6, #306
- PR参照: #311, #276
- 主見出し: ## 目的・背景 | ### 利用者価値 | ## 現状と根拠 | ## 現時点の評価（レビューアの判定を引き継ぐ） | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - 不一致時のメッセージに「どちらを更新すべきか（写しの `synced-from` を現在値へ）」を含める。
- - `check-governance-drift.sh` 自体の挙動変更（fail-open・PostToolUse 限定は現行のまま）。
- - [ ] `tests/unit/` に synced-from 同期を検査するテストが存在し、現状の repo で **pass** する。
- - [ ] fail 時のメッセージに、現在の sha と写しに記録された sha の**両方**が出る（何をどう直すか分かる）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
