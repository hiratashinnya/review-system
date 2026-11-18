# Issue #340「agent-command-gate.sh は内部例外で fail-open する（deny すべき呼び出しが素通しになる）」

- URL: https://github.com/hiratashinnya/review-system/issues/340
- 状態: closed（2026-11-18取得）
- 本文: 2857文字/ 84行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 5件（未チェック: 5）
- Issue参照: #308, #129, #339, #227, #224
- PR参照: なし
- 主見出し: ## 目的・背景 | ### 利用者価値 | ## 現状と根拠 | ## 提案挙動 | ### 案A（推奨）: 例外を deny に落とす | ### 案B: ロール登録の一貫性を実行時に検査する | ### 不採用案 | ## 互換性 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - **デメリット**：フックのバグが「作業が全部止まる」形で顕在化する（ただし現状は
- - 対象外ロール（main context 等）の fail-open は**別の話**で、こちらは 2026-07-11 の
- - `GATED_ROLES` 外ロールの fail-open（オーナー確定済みの設計・2026-07-11）。
-   stderr 検査を入れる対症のみ行い、フック本体の fail-open は本 Issue に分離した。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
