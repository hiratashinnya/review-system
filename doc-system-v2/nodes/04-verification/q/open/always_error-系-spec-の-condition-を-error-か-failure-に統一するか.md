**status: open**

**論点（Issue #78 論点3）**: `always_error` 系ルール（抑制不可・RULE-005 孤立 / RULE-007 存在しない ID 参照）を検査する SPEC の condition が不揃いになっている。**FND-83**（open・INFO）の指摘を語彙再設計に取り込み、付与基準を統一するか。

**現状**:
- `config.yml` の `always_error: [RULE-005, RULE-007]`（scheduled/suppress/activate_stage いずれでも抑制不可）。
- 対応 SPEC の condition が不揃い:
  - **SPEC-6**「存在しない ID 参照を RULE-007 ERROR 報告」（v0.1.0）→ `condition: error`
  - **SPEC-7**「孤立ノードの検出」（RULE-005・v0.2.0）→ `condition: failure`
- 両者は同じ always_error 性質だが、condition 軸の付与基準が一貫していない（error か failure か）。FND-83 が「付与基準を統一定義せよ」と指摘。
- セマンティクス上の含意: `failure`＝仕様違反を正しく検出（sad-path）/ `error`＝処理不能な異常入力（fail-close 対象）。RULE-005（孤立）も RULE-007（dangling 参照）も「グラフ構造の違反を検出する sad-path」であり、入力が処理不能なわけではない。この観点では両者とも `failure` が自然に見える。一方 always_error（抑制不可・fail-close）という運用面を重視すると `error` が自然にも見える。ここが不揃いの根本。

**選択肢**:
- **A（両者を `failure` に統一・SPEC-6 を failure へ）** — 「検査対象の仕様違反を検出する sad-path」という等価分割の意味を優先。RULE-005/007 は「構造違反を正しく検出する」テストなので failure が語彙定義に忠実。SPEC-6 の condition を error→failure に変更。トレードオフ＝always_error（抑制不可）という運用属性は condition とは別軸（config の always_error リスト）で既に表現されており、condition を error にする必要はない、という整理が要る。
- **B（両者を `error` に統一・SPEC-7 を error へ）** — always_error（fail-close・抑制不可）＝最も重い異常という運用面を condition にも反映。SPEC-7 の condition を failure→error に変更。トレードオフ＝error の語彙定義「処理不能な異常入力（fail-close 対象）」と、RULE-005/007 が検査するもの（＝入力自体は処理可能で、グラフ構造が違反）がずれる。condition の意味を「入力の性質」から「違反の重大度」へ読み替えることになり、5値の等価分割セマンティクスが濁る（論点2 と衝突）。
- **C（統一しない・付与基準を「検査が扱う入力の性質」で個別判定と規約化）** — condition は always_error 性ではなく「その SPEC が扱う入力の等価クラス」で決めると規約に明記し、SPEC-6=error（存在しない ID＝不正参照で処理不能）/ SPEC-7=failure（孤立＝構造違反の検出）を意図的な差として正当化する。トレードオフ＝FND-83 の「不一致」がそもそも指摘でなく意図的差だったことになり、基準の明文化で解消。ただし「存在しない ID 参照」を error、「孤立」を failure とする境界が本当に妥当かは要吟味。

**推奨**: **A（両者 failure 統一）を第一候補**、**C（基準明文化で個別判定）を次点**。理由：(1) condition の5値は「入力の等価クラス」であり、always_error（抑制不可）は別軸（config の always_error リスト）で既に表現済み。二重に condition へ載せる（B）と等価分割が濁り論点2 と衝突するため B は非推奨。(2) RULE-005/007 はどちらも「グラフ構造違反を検出する sad-path」であり failure が語彙定義に忠実。(3) ただし「存在しない ID 参照」を error 扱いする現行にも「参照先が無い＝処理不能」という一理があり、これを意図的差として残すなら C（基準明文化）。A と C の分岐は「RULE-007 が扱う入力を failure と見るか error と見るか」に帰着し、**オーナー判断**。

**論点4（整合連動）への波及**: SPEC-6/7 の condition を変更すると、それらを verifies する TD が存在する場合 **RULE-019**（TD↔SPEC condition 一致）に波及する（TD 側 condition も追随変更が必要）。論点4 の Q で RULE-019 との整合を確認する。

**他論点との結合**: 本 Q（論点3）は論点2（vocab セット）が確定した集合内での値の割り当て。論点2 が B/C（セット変更）なら本 Q の選択肢も影響を受けるため、論点2 → 論点3 の順で決めるのが自然。independent な決定軸（always_error への値割当基準）のため別 Q とした。

**ブロッカー**: always_error 系の condition 統一方針は**オーナー判断**。実施時期も含めてオーナーが決定する（**独断でのスプリント繰越は禁止**・`scheduled` 空で判断を仰ぐ）。決定後は DD へ昇格し FND-83 を解消（`backref` ツールで辺逆転）。

**指摘時 ref_version**: always_error 系 SPEC の condition が不揃い（SPEC-6=error, SPEC-7=failure）"0.1"（FND-83 サイドカー v0.1.0 時点）／存在しない ID 参照を RULE-007 ERROR 報告 "0.1"（同 SPEC サイドカー v0.1.0 時点）／孤立ノードの検出 "0.2"（同 SPEC サイドカー v0.2.0 時点）
