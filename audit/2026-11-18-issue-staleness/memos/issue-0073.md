# Issue #73「Sub-D: 著作パイプライン更新（*-author / reconciliation-validator / reconciliation）」

- URL: https://github.com/hiratashinnya/review-system/issues/73
- 状態: closed（2026-11-18取得）
- 本文: 787文字/ 19行。全文: `../raw/issues-2026-07a.jsonl`
- AC: 0件（未チェック: 0）
- Issue参照: なし
- PR参照: なし
- 主見出し: ## 目的 | ## スコープ | ## 受け入れ条件
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - **reconciliation**：書込先を `nodes/<stage>/<type>/[status]/` のペアに。**status 遷移（open→resolved 等）を `git mv` で機械実行**（backref 逆転と同梱）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
