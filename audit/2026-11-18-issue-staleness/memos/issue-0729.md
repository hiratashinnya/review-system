# Issue #729「fix(asset_parity): CIのGit履歴不足とstaleness診断の再現性・表示を改善する」

- URL: https://github.com/hiratashinnya/review-system/issues/729
- 状態: closed（2026-11-18取得）
- 本文: 3206文字/ 68行。全文: `../raw/issues-2026-11.jsonl`
- AC: 7件（未チェック: 7）
- Issue参照: #581, #468, #617, #637
- PR参照: なし
- 主見出し: ## 目的・背景 | ### 確認済み実測 | ## Scope | ## Out of scope | ## Acceptance criteria | ## 対象ファイル（候補） | ## Dependencies / Related
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - 現在のflagには新規の `gh-create-issue`（Codex skill）と `issue-pipeline`（Copilot skill）も含まれる。後者は[Issue #468](https://github.com/hiratashinnya/review-system/issues/468)で **薄いwrapperを維持しstalenessを許容** する方針が確定済み。
- - **Blocked by:** なし

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
