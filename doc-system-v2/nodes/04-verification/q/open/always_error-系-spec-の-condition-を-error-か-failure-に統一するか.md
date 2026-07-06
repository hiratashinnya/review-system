**status: open**

**論点（Issue #78 論点3）**: `always_error` 系ルール（抑制不可・RULE-005 孤立 / RULE-007 存在しない ID 参照）を検査する SPEC の condition が不揃いになっている。**FND-83**（open・INFO）の指摘を語彙再設計に取り込み、付与基準を統一するか。

**現状**:
- `config.yml` の `always_error: [RULE-005, RULE-007]`（scheduled/suppress/activate_stage いずれでも抑制不可）。
- 対応 SPEC の condition が不揃い:
  - **SPEC-6-1**「存在しない ID 参照を RULE-007 ERROR 報告」（v0.1.0）→ `condition: error`（傘 SPEC「存在しない ID への参照」の子）
  - **SPEC-7**「孤立ノードの検出」（RULE-005・v0.2.0）→ `condition: failure`
- 両者は同じ always_error 性質だが、condition 軸の付与基準が一貫していない（error か failure か）。FND-83 が「付与基準を統一定義せよ」と指摘。
- セマンティクス上の含意: `failure`＝仕様違反を正しく検出（sad-path）/ `error`＝処理不能な異常入力（fail-close 対象）。RULE-005（孤立）も RULE-007（dangling 参照）も「グラフ構造の違反を検出する sad-path」であり、入力が処理不能なわけではない。この観点では両者とも `failure` が自然に見える。一方 always_error（抑制不可・fail-close）という運用面を重視すると `error` が自然にも見える。ここが不揃いの根本。

**選択肢（起票時）**:
- **A（両者を `failure` に統一・SPEC-6-1 を failure へ）** — 「検査対象の仕様違反を検出する sad-path」という等価分割の意味を優先。RULE-005/007 は「構造違反を正しく検出する」テストなので failure が語彙定義に忠実。SPEC-6-1 の condition を error→failure に変更。トレードオフ＝always_error（抑制不可）という運用属性は condition とは別軸（config の always_error リスト）で既に表現されており、condition を error にする必要はない、という整理が要る。
- **B（両者を `error` に統一・SPEC-7 を error へ）** — always_error（fail-close・抑制不可）＝最も重い異常という運用面を condition にも反映。SPEC-7 の condition を failure→error に変更。トレードオフ＝error の語彙定義「処理不能な異常入力（fail-close 対象）」と、RULE-005/007 が検査するもの（＝入力自体は処理可能で、グラフ構造が違反）がずれる。condition の意味を「入力の性質」から「違反の重大度」へ読み替えることになり、5値の等価分割セマンティクスが濁る（論点2 と衝突）。
- **C（統一しない・付与基準を「検査が扱う入力の性質」で個別判定と規約化）** — condition は always_error 性ではなく「その SPEC が扱う入力の等価クラス」で決めると規約に明記し、意図的な差として正当化する。トレードオフ＝FND-83 の「不一致」がそもそも指摘でなく意図的差だったことになり、基準の明文化で解消。ただし境界の妥当性は要吟味。
- **D（欠落 condition 用の兄弟 SPEC を新設・オーナー仮説の選択肢化）** — 各規則が failure と error の**両方の兄弟 SPEC** を持つべきという前提で、欠落側の condition を担う兄弟 SPEC を新設する。**評価は下記「再フレーミング後の結論」で不採用**。

**オーナー指摘（2026-07-06）による再フレーミング**: オーナー＝「どっちに統一でもいいが、そもそも failure と error 両方無いと SPEC として充足してないのでは？」。この指摘を受け、当初の「単一 condition へ**統一**する」というフレーミング自体を再検証した。結論として **「統一」は誤ったフレーミングであり、かつ本ファミリーに網羅穴は無い**（＝欠落側の兄弟 SPEC 新設も不要）ことがコーパス確認で判明した。根拠：

- **カバレッジは FR 粒度で規定される（RULE-017/018 を再読）**: `coverage_rules.fr` = `required_conditions: [normal]` / `recommended_conditions: [failure, error]`。RULE-018 の実 SPEC「fr-の-spec-群に-failure-error-condition-なし-rule-018」の期待動作は「FR の SPEC 群に `condition: failure` **も** `condition: error` **も**存在しない → WARNING」＝**OR セマンティクス**（どちらか一方があれば充足・両方同時保有は要求しない）。すなわち config 上「1 つの規則（RULE）ごとに failure と error を両方持て」という要件は存在しない。
- **SPEC-6・SPEC-7 は同一 FR ファミリー「構造的完結性検証」に属し、その FR は既に normal/failure/error を全網羅**: 実 slug と親をコーパスで特定した結果——
  - SPEC-7＝`孤立ノードの検出`（RULE-005・condition: **failure**）は FR「構造的完結性検証」の直接の子。
  - SPEC-6＝傘 SPEC `存在しない ID への参照`（condition: error・**傘**）が同 FR の子で、そのテスタブル子 SPEC-6-1＝`存在しない ID 参照を RULE-007 ERROR 報告`（condition: **error**）。
  - 同 FR ファミリーには normal も存在（`整合グラフは構造違反 0 で通過` = normal）。ほか多数の必須辺欠如系 SPEC が failure。
  - ∴ FR「構造的完結性検証」は **normal ✓ / failure ✓ / error ✓** を既に全て保有。RULE-017・RULE-018 とも充足済みで**網羅穴なし**。オーナーの「両方無いと充足してない」懸念への答え＝「**このファミリーは failure も error も既に保有しており充足している**」。
- **RULE-005/007 は各々「単一の入力等価クラス」しか持たない**: condition の 5 値は「その SPEC が扱う入力の等価クラス」。RULE-005（孤立）も RULE-007（存在しない ID 参照）も、**パース可能な入力に対しグラフ構造違反を検出する sad-path** ＝ 本来 **failure クラス**。両規則に「処理不能な異常入力（error クラス）」の別入力は存在しない——error クラス（YAML 構文不正・UTF-8 デコード失敗・id 欠如等）は別 SPEC ファミリーが既にカバー済み。∴ RULE-005/007 の各規則に error 兄弟を新設する必要はない（1 規則 = 1 入力クラスで充足）。

**再フレーミング後の結論**: 論点の本質は「どちらの label に統一するか」でも「欠落 condition の兄弟 SPEC 新設か」でもなく、**「各 SPEC の condition を、その規則が扱う入力等価クラスに従って個別に正しく割り当てる」**ことである。この基準で見ると、SPEC-6-1（RULE-007 検出）の現行 `condition: error` は、**always_error という運用属性（fail-close・抑制不可）を入力等価クラスに誤って持ち込んだ誤割当**である（always_error は既に config の `always_error` リスト＋子 SPEC「always_error による抑制不可」で別軸表現済み）。正しくは SPEC-6-1 も **failure**（構造違反を検出する sad-path）。→ 元の選択肢 **A（両者 failure）** が結論だが、その根拠は「統一」ではなく「**入力等価クラスに基づく個別割当の是正**」。C（基準明文化）は A と両立し、「condition は always_error 性でなく入力等価クラスで決める」規約として併せて明文化する。

- **D の評価＝不採用**: (1) カバレッジは FR 粒度で既に normal/failure/error を全網羅済み（穴なし）。(2) RULE-005/007 は各々単一入力クラス（failure）しか持たず、error クラスの別入力が実在しない（error は別 SPEC ファミリーが担当）。∴ 新設すべき欠落兄弟は無い。オーナーの鋭い問いは「統一」フレーミングの誤りを正しく露呈したが、網羅穴の存在は示さない。

**論点4（整合連動）への波及**: SPEC-6-1 の condition を error→failure に是正すると、それを verifies する TD が存在する場合 **RULE-019**（TD↔SPEC condition 一致）に波及する（TD 側 condition も追随変更が必要）。論点4 の Q で RULE-019 との整合を確認する。傘 SPEC「存在しない ID への参照」の `condition: error` 残存は論点1（傘＝condition 省略）の処置で解消する（本 Q の scope 外）。

**他論点との結合**: 本 Q（論点3）は論点2（vocab セット）が確定した集合内での値の割り当て。論点2 が B/C（セット変更）なら本 Q の選択肢も影響を受けるため、論点2 → 論点3 の順で決めるのが自然。independent な決定軸（always_error への値割当基準）のため別 Q とした。

**ブロッカー**: always_error 系の condition 是正方針（A＝入力等価クラス基準で SPEC-6-1 を failure へ）は**オーナー判断**。実施時期も含めてオーナーが決定する（**独断でのスプリント繰越は禁止**・`scheduled` 空で判断を仰ぐ）。決定後は DD へ昇格し FND-83 を解消（`backref` ツールで辺逆転）。

**指摘時 ref_version**: always_error 系 SPEC の condition が不揃い（SPEC-6=error, SPEC-7=failure）"0.1"（FND-83 サイドカー v0.1.0 時点）／存在しない ID 参照を RULE-007 ERROR 報告 "0.1"（同 SPEC サイドカー v0.1.0 時点）／孤立ノードの検出 "0.2"（同 SPEC サイドカー v0.2.0 時点）
