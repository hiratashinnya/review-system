# Issue #296「Issue/PRで共有するblocker dependency resolverを実装する」

- URL: https://github.com/hiratashinnya/review-system/issues/296
- 状態: closed（2026-11-18取得）
- 本文: 2558文字/ 71行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 10件（未チェック: 10）
- Issue参照: #294, #295, #298, #299, #273, #293
- PR参照: なし
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## 利用者価値 | ## 提案挙動 | ## Scope | ## Out of scope | ## 互換性 | ## 代替案 | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- 現在は依存を各 workflow/skill が人手で解釈する。別実装にすると pagination、自動 close、cycle、障害時挙動が drift する。#294 は API と無料構成の意思決定を完了し、resolver 自体の挙動 fixture を本 Issue の implementation validation へ移管した。
- - Issue mode は open blocker の推移閉包を返す
- - #294 から移管された open / closed blocker、direct / transitive relation、cycle、pagination、partial response、API failure、権限不足の resolver fixture
- - 既存の native blocked-by、parent/sub-issue relation を正本として読み取り、既存 relation を自動変更しない
- - Issue 本文の `Blocked by` 文字列だけを解析する案は native relation との不一致を防げないため正本にしない
- - [ ] #294 から移管された direct、open / closed、transitive、cycle、pagination、partial response、API failure、権限不足を resolver fixture でテストする
- - [ ] parent close 後の open sub-issue、same-PR child close、手動 parent 早期 close を closure invariant evaluator の unit fixture でテストする
- - Blocked by: #295

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
