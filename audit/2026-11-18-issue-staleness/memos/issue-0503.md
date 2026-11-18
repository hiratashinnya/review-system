# Issue #503「karte check が disposition: deferred/waived の finding にも診断を要求し、停止ゲートが毎ラウンド必ず 1 回 block する」

- URL: https://github.com/hiratashinnya/review-system/issues/503
- 状態: closed（2026-11-18取得）
- 本文: 7552文字/ 145行。全文: `../raw/issues-2026-09.jsonl`
- AC: 9件（未チェック: 9）
- Issue参照: #493, #495, #491, #502, #489, #500
- PR参照: #500
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## 影響 | ## root cause 仮説 | ## 提案挙動 | ### 代替案（比較） | ## Scope | ## 観測2：`karte append --change-kind` の語彙に文書のみの変更を表す値が無い（別 root cause・2026-09-08 追記） | ### 観測2の実測（2026-09-08・Issue #493 の是正ラウンド2） | ### 観測2の実害 | ## 観測3：無進捗検知（3ラウンド連続未解消）も `disposition: deferred` を除外しない（2026-09-08 追記） | ### 観測3の実測（2026-09-08・Issue #493 の round 3 取り込み後）
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - F-493-04 は `karte status` 上 `harm: real` / `scope: out` / **`disposition: deferred` / `deferred_to: #491`**（オーナー判断・2026-09-08 確定）。同じ `status` の出力では「申し送り（disposition: deferred・status は open のまま）: F-493-04→#491」として **clean を妨げない側に
- Issue #495 の実装が `disposition` による除外を `status` の verdict 算出（`blocking_harmful` の定義）にだけ入れ、`check` の診断網羅判定へ反映しなかった。`check` は #495 より前から存在し、「未解消 finding = 診断が要る finding」という前提のまま残っている。
- 根拠は `karte/README.md` が既に述べている二層構造そのもの——`deferred` / `waived` は「当該 PR では処置しないとオーナーが決めた」finding であり、`status: open` のまま台帳に残す一方で **verdict の上でだけ** clean を妨げなくする。是正担当に診断を求めるのは「これから直す finding」に対してであって、「直さないと決まった finding」に対してではない。
- - **(b) `check` は現状のまま、`deferred` の finding にも「診断不要」を明示する新しい記録を求める** — 二重記録になり、`disposition` を導入した意味が薄れる。却下寄り。
- - `karte/README.md` に `check` の判定規則を明記する（現在は `status` の verdict 側だけが説明されている）。
- verdict: harmful-open（clean を妨げる実害ありが残存）
-   clean を妨げる実害あり（verdict harmful-open を成立させている集合）: F-493-11
-   申し送り（disposition: deferred・status は open のまま）: F-493-04→#491, F-493-07→#502,

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
