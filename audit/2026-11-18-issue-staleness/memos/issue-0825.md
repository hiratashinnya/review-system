# Issue #825「feat(change-plan): live検証の要否判定とケース証拠を既存CPへ接続する（S6）」

- URL: https://github.com/hiratashinnya/review-system/issues/825
- 状態: open（2026-11-18取得）
- 本文: 1431文字/ 22行。全文: `../raw/issues-2026-11.jsonl`
- AC: 5件（未チェック: 5）
- Issue参照: #733, #652, #371
- PR参照: #733
- 主見出し: ## 目的・成果 | ## Scope | ## AC（[AC-S6全5項目](https://github.com/hiratashinnya/review-system/blob/main/audit/2026-11-03-pr-issue-mistake-patterns/DESIGN-S4-S6.md)） | ## 検証 | ## 共通の実装・レビュー境界
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- - case_id、repo/branch/OID、role/PF、前提、期待/実際、run ID・ログ・digest、結果pass/fail/blocked/not_run、followupを残す。
- - 起票は実装開始順や未決事項のオーナー承認を意味しない。着手時にmain、OPEN PR、既存Issue、成果物責務と競合を再確認する。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
