# Issue #472「MAX_SNAPSHOT_AGE_SECONDS の直上コメントに、F-470-02 で否定した旧因果が残っている」

- URL: https://github.com/hiratashinnya/review-system/issues/472
- 状態: closed（2026-11-18取得）
- 本文: 2534文字/ 58行。全文: `../raw/issues-2026-09.jsonl`
- AC: 6件（未チェック: 6）
- Issue参照: #471, #470, #460
- PR参照: #471
- 主見出し: ## 目的・背景 | ## 現状と根拠 | # snapshot の鮮度上限（秒）。gate は staleness 10 分で fail-close するが、 | # 本ツールは 15〜30 分周期のため同じ値だと通常運転で自分を弾く。60 分なら | # 通常運転では発火せず、blocker-snapshot が実際に停止した異常だけを捕まえる。 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
抽出なし

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
