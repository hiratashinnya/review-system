# Issue #284「agy-mcp-bridge のローカルパッチを更新・再 clone 後も安全に維持する」

- URL: https://github.com/hiratashinnya/review-system/issues/284
- 状態: open（2026-11-18取得）
- 本文: 2342文字/ 60行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 6件（未チェック: 6）
- Issue参照: #259, #273, #290, #270
- PR参照: #259
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues | ## Current state / Target state | ## Migration / Rollback | ## Compatibility | ## Security impact
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- PR #259 が前提とする、repository 外の `agy-mcp-bridge` への最小権限ローカルパッチを、更新・再 clone 後も失わず安全に再現できる状態にする。
- - Migration: 現在稼働中の bridge version とローカル差分を採取し、再現可能な patch artifact に固定する。clean install へ同 artifact を適用し、正常系・patch 欠落・未知 version・存在しない workspace の各検証後に利用経路を切り替える。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
