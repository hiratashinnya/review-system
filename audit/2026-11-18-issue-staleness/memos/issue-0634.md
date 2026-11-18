# Issue #634「[pages] PRとPagesのテスト探索起点を揃え、全suiteのcoverageを合算する」

- URL: https://github.com/hiratashinnya/review-system/issues/634
- 状態: closed（2026-11-18取得）
- 本文: 3460文字/ 70行。全文: `../raw/issues-2026-10.jsonl`
- AC: 5件（未チェック: 5）
- Issue参照: #587, #213, #600, #214, #602, #215, #624, #578
- PR参照: #587, #600, #602, #624
- 主見出し: ## 問題と期待する挙動 | ## 確認した事実と根拠 | ### 発生境界 | ## 採用方針・Scope（案A） | ## Out of scope | ## Acceptance criteria | ## 調査と起票の実施範囲
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - `-s tests` では `unit.test_feedback_ledger_*` として読み込まれ、トップレベルのヘルパー import が失敗する。探索起点と import 前提の不一致が原因である可能性が高く、ログ・設定・差分が一致する。
- - Pages の探索起点を PR チェックと揃え、現状の `tests/unit`、`tests/time_fixture_lint`、`tests/jev_hooks` をそれぞれ直接探索する。
- 採用理由：既存の import 前提に合う探索方式を両 workflow で共有し、PR では通るが main で失敗する差を解消できるため。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
