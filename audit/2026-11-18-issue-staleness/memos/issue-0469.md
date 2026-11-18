# Issue #469「blocker_gate の UrlLibReadTransport が「読み取り専用」と名乗りながら POST を公開している（名前と実体の不一致）」

- URL: https://github.com/hiratashinnya/review-system/issues/469
- 状態: closed（2026-11-18取得）
- 本文: 2214文字/ 43行。全文: `../raw/issues-2026-09.jsonl`
- AC: 4件（未チェック: 4）
- Issue参照: #465, #460, #345, #434
- PR参照: #465
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- 同クラスは docstring に「GitHub resource を変更するメソッドを公開しない」旨を書いているが、実際には **POST を公開しており、GraphQL mutation にも使える**。現状の呼び出し箇所はすべて read であり実害は出ていないが、**名前と docstring が実体を保証していない**。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
