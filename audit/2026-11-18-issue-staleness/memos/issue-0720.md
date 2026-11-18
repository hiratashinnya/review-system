# Issue #720「回帰を検出できない（恒真・欠落）テスト: TestStatus.test_clean と trigger の batch コマンド型検査」

- URL: https://github.com/hiratashinnya/review-system/issues/720
- 状態: closed（2026-11-18取得）
- 本文: 2238文字/ 52行。全文: `../raw/issues-2026-11.jsonl`
- AC: 5件（未チェック: 0）
- Issue参照: #696, #719
- PR参照: #696
- 主見出し: ## 対象 harness | ## 目的・背景 | ## 現状と根拠 | ### T10: `TestStatus.test_clean` の最後の assert が恒真 | ### T09: `karte_notify/trigger.py` の batch コマンド型検査を固定するテストが無い | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - 問題: `status` の本文出力には `clean を妨げる未解消` などの行（`karte/README.md`「`harm: real` の 3 集合」の説明参照）や `harmful-open（clean を妨げる…）` のようなラベルがあり、部分文字列 `"clean"` は verdict が `clean` でなくても出力に含まれる。
- - レビューの実測: `if not blocking: verdict = "clean"` を `"harmful-open"` に書き換えても、このテストは PASS する。
- - [x] `test_clean` が verdict 行の `clean` を assert する（`harmful-open` など別 verdict や、ラベル中の "clean" では通らない）。
- - [x] 変異 `if not blocking: verdict = "clean"` → `"harmful-open"` で `test_clean` が失敗することを確認し、PR 本文に記録する。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
