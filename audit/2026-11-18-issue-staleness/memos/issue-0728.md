# Issue #728「回帰を検出できないテスト（続）: karte_notify の入力ガード未検証と、karte テストの緩い終了コード断定」

- URL: https://github.com/hiratashinnya/review-system/issues/728
- 状態: closed（2026-11-18取得）
- 本文: 3784文字/ 72行。全文: `../raw/issues-2026-11.jsonl`
- AC: 5件（未チェック: 0）
- Issue参照: #696, #720, #719, #721, #722
- PR参照: #696
- 主見出し: ## 対象 harness | ## 目的・背景 | ## 現状と根拠 | ### 1. 未検証の入力ガード（変異が生存） | ### 2. 緩い終了コード断定 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- | `karte_notify/hook.py` 77-90 行（`_status_payload`） | `runner` が投げる例外を `except Exception` で受け、`None`（fail-open）にする | `subprocess.TimeoutExpired` の握りつぶしを `OSError` に絞っても全テストが通る。`STATUS_TIMEOUT_S = 30` があるため、現実に起きる経路 |
- - 上表 4 つのガードのそれぞれを固定するテストを追加する。`TimeoutExpired` は「`runner` が `subprocess.TimeoutExpired` を投げたとき fail-open（無出力・終了コード 0・`STATUS_UNAVAILABLE` の evidence）になる」ことを固定する。
- - [x] `runner` が `subprocess.TimeoutExpired` を投げる入力で fail-open になるテストがある。`except Exception` を `except OSError` に絞る変異でそのテストが失敗することを確認し、PR 本文に記録した。
- - parent／sub-issue／blocked-by: なし。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
