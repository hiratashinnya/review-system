# Issue #495「レビューのスコープ外指摘が実害判定とカルテを迂回でき、実害ありの指摘が未処置のまま merge される」

- URL: https://github.com/hiratashinnya/review-system/issues/495
- 状態: closed（2026-11-18取得）
- 本文: 7390文字/ 138行。全文: `../raw/issues-2026-09.jsonl`
- AC: 10件（未チェック: 10）
- Issue参照: #490, #488, #493, #370, #371, #431
- PR参照: #490
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## 再現（実際に起きた事象） | ## 期待結果 / 実際結果 | ## root cause | ## 影響 | ## 提案挙動（オーナー確定：2026-09-07） | ### 1. カルテの finding を一本化する | ### 2. finding に `scope` 属性を追加する | ### 3. `harm: real` にはオーナー判断の記録を必須にする | ### 4. `karte status` の verdict をゲートにする | ### 5. `deferred` を `resolved` にしない（fail-open 防止）
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
-    `karte/cli.py` の `_status_payload` は `karte.open_findings()` から `clean` / `harmful-open` / `no-harm-only` を決める。カルテに入っていない指摘は verdict に一切影響しない。
- 5. merge 後にオーナー指摘を受けて実害判定をやり直したところ、当該指摘は `issue-pipeline` の実害定義の項4（後工程の誤読・暗黙の前提・観測不能）に該当する **`harm: real`** であることが確定し、#493 として起票された。
- ### 5. `deferred` を `resolved` にしない（fail-open 防止）
- `status: resolved` は「当該 PR で実際に直った」だけに限定する。`deferred` は `status: open` のまま残し、**verdict の上でだけ clean を妨げない**という二層にする。`deferred` を `resolved` にすると「別 Issue へ移したと書くだけで指摘が消える」経路ができ、本 Issue が塞ごうとしている穴が別の形で再発する。
- - [ ] `deferred` の finding が `status: open` のまま残り、`resolved` と区別できる。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
