# Issue #826「feat(safety): 安全重要verbのactor・target・OIDをtrusted bindingへ束縛する（L3）」

- URL: https://github.com/hiratashinnya/review-system/issues/826
- 状態: open（2026-11-18取得）
- 本文: 1458文字/ 24行。全文: `../raw/issues-2026-11.jsonl`
- AC: 6件（未チェック: 6）
- Issue参照: #733, #706, #745, #757, #761
- PR参照: #733
- 主見出し: ## 目的・成果 | ## Scope | ## AC（[AC-L3全6項目](https://github.com/hiratashinnya/review-system/blob/main/audit/2026-11-03-pr-issue-mistake-patterns/DESIGN-L1-L3.md)） | ## 着手前の競合管理 | ## 共通の実装・レビュー境界
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- - まず安全重要verbごとのactor/role、対象、side effect、allow/deny/unknown、owner承認条件の表を確定する。適用範囲の拡大はオーナー判断を前提とする。
- - 起票は実装開始順や未決事項のオーナー承認を意味しない。着手時にmain、OPEN PR、既存Issue、成果物責務と競合を再確認する。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
