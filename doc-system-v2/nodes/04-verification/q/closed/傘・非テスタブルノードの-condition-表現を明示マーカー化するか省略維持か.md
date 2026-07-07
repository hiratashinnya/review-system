**status: closed**（2026-07-06 DD へ昇格・決定済み）

**論点（Issue #78 論点1）**: 傘（アンブレラ）ノード・非テスタブルノードの condition をどう表現するか。現状は「傘ノードは condition を省略する」方式（Sub-A 採用・#81 で umbrella は condition 値でなくなった）で運用している。これで十分か、それとも明示マーカーや別属性が要るか。本 Q が決定されると既存の **FND-89**（傘 SPEC の condition が子の condition 多様性を代表せずミスリード・open・INFO）が解消される。

**現状**:
- `config.yml` の condition_vocab は `[normal, boundary, empty, failure, error]` の5語。コメントに「非テスタブル(傘)ノードは condition を持たない」と明記され、傘は condition **省略**で表す。
- slugify.py も umbrella マーカーを condition 語彙から外し（`（umbrella）` は strip 対象外）、傘＝condition 不在という設計で一貫している。
- 一方で **RULE-016** は「SPEC/TD に condition 属性がない、または語彙外の値」を ERROR 報告する。傘 SPEC が condition を省略すると、この RULE-016 と衝突しない運用上の前提（＝傘は RULE-016 の対象外）が config コメント・notation の散文にのみ存在し、機械可読な区別が無い。
- **FND-89 の指摘**: アンブレラ SPEC-44（condition: normal）の子は SPEC-44-1=normal / SPEC-44-2=boundary / SPEC-44-3=error と多様で、傘の condition が normal 固定だと子の多様性を代表せずミスリードを招く。傘から condition を外すと RULE-016 に抵触するというジレンマ。※FND-89 は現状 SPEC-44 に `condition: normal` が残る前提での指摘であり、「傘＝省略」への統一が未徹底の箇所が残っている可能性を含む。

**選択肢**:
- **A（省略維持・傘を RULE-016 対象外と規約で明文化）** — 現行の「傘は condition 省略」を維持し、RULE-016 の検査対象から傘ノードを除外する条件（例: 子 SPEC を持つ＝被参照 SPEC は傘とみなす等の機械判定基準）を config/notation に明文化する。傘に残っている `condition: normal` は省略へ統一する。トレードオフ＝「傘か否か」を機械判定する基準を新設する必要があり、その基準（子 SPEC の有無か、明示フラグか）自体が別の設計論点になる。
- **B（明示マーカー導入・専用値 `mixed`/`umbrella` を condition に追加）** — 傘に専用の condition 値（例 `umbrella` または `mixed`）を持たせ、RULE-016 を満たしつつ「代表 condition ではない＝子が多様」を機械可読に表す。トレードオフ＝condition_vocab に等価分割クラスでない値が混じり、5値の意味（等価分割）が濁る。RULE-019（TD↔SPEC condition 一致）・coverage_rules との相互作用も再定義が要る（論点4 と連動）。
- **C（別属性導入・`testable: false` フラグを新設）** — condition とは別に「非テスタブル/傘」を表すブール属性を新設し、condition の等価分割セマンティクスを汚さずに傘を表現する。RULE-016 は `testable: false` のノードを対象外にする。トレードオフ＝サイドカーのキーが増える（現状「未知キー禁止」の schema 変更が必要）。ただし機械判定と意味分離は最も明快。

**推奨（起票時）**: **A（省略維持＋傘の機械判定基準を明文化）を第一候補**、**C（別属性）を次点**。理由：(1) 現行は既に「傘＝省略」で運用実績があり、破壊的変更が最小。(2) B は等価分割クラスでない値を vocab に混ぜ、論点2/4 の整合を複雑化するため非推奨。(3) A の弱点（傘の機械判定基準が未定義）は、C（明示 `testable: false`）で補える。A で基準を明文化しきれない場合は C へ。**いずれもオーナー判断**。

**オーナー回答（2026-07-06）と結論**: オーナー指示＝「別属性で子ノードを持ってるかどうかを判定。testable 以外の名前を検討して」。これは **condition とは別の情報（＝サイドカーの `edges` という既存の構造）を見て傘性を機械判定せよ**という指示であり、`FORMAT.md`（L76）の既定原則「傘性は『同型の子から被参照される』構造から導出する（condition に umbrella を混ぜない）」の**追認・具体化**である。したがって選択肢 **A（省略維持＋機械判定基準の明文化）を採用**する。B（専用 condition 値）は等価分割 vocab を濁すため不採用、C（`testable: false` 等の格納属性新設）はオーナーが求める「構造からの判定」ではなく新規キーを増やす（schema 未知キー禁止に抵触）ため不採用。

- **機械判定基準（A の未定義弱点を確定）**: 「**同型の子から親向き依存辺で被参照される SPEC ＝ 傘**」とする。具体的には、ある SPEC が別の SPEC から `SPEC→SPEC`（子→親 refines）辺の `to` に指されている（＝同型の被依存辺を持つ）なら傘。meta.json/edges から決定論的に導出でき、格納属性を増やさない。**RULE-016 はこの傘ロールのノードを検査対象外**にする（傘は condition を持たない）。
- **呼称（testable 以外の命名検討・2〜3案）**:
  1. **umbrella / leaf（傘 / 葉）** ＝ 傘＝同型の子から被参照される非テスタブルノード、葉＝condition を持つテスタブル末端アサーション。**本コードベースで既に「傘/umbrella」が正準語彙**（FORMAT.md・config コメント・FND-89）であり、追加語彙を導入せず最も自然。**推奨**。
  2. `role: hub / leaf` ＝ グラフ汎用だが「hub」は高次数（fan-in/out 大）を含意し「抽象親」を正確に表さない。新語彙を導入する分だけ既存文脈から乖離。
  3. `abstract / concrete`（抽象 / 具体）＝ OOP 由来で明快だが doc-system の既存語彙にない新語彙。
  → **呼称は #1「umbrella（傘）/ leaf（葉）」を採用**（既存語彙の追認）。傘は格納値でなく **edges から導出されるロール**であり、config/notation では「傘ロール（＝同型の子→親辺の target になっている非葉 SPEC）は RULE-016 対象外」と明文化する。
- **残存 condition のクリーンアップ（本決定の処置に含める）**: 現状、傘 SPEC「存在しない ID への参照」に `condition: error` が、FND-89 の SPEC-44 に `condition: normal` が**残っている**（傘＝省略への統一が未徹底）。DD 昇格時にこれら傘 SPEC の condition を**省略へ統一**し、FND-89 を解消する。

**論点4（整合連動）への波及**: 本決定は RULE-016（condition 必須検査）の対象範囲に直接影響する。A を採用したため vocab セット（論点2）・RULE-019 への波及はなく、影響は「RULE-016 に傘ロール除外条件を追加する」1 点に限定される。out-of-graph 資産（接続マトリクス・notation・各 author）へは「傘ロールは edges 由来で判定・RULE-016 対象外・condition 省略」の明文化を伝播する。

**他論点との結合**: 本 Q（論点1）は論点2（5値セット）・論点3（always_error）と condition 語彙という同一主題を共有するが、傘表現は「テスタブル/非テスタブルの区別」という独立した決定軸のため別 Q として起票した（1論点1Q・Issue #78 の4点に1:1対応）。A 採用により vocab には手を入れないため論点2 との統合判断は不要。

**ブロッカー**: 傘 condition の表現方式は**オーナー判断**。オーナー回答（A 採用・呼称 umbrella/leaf）を得たため方式は確定。実施時期（今スプリント vs 次スプリント以降）は引き続きオーナー判断（**独断でのスプリント繰越は禁止**＝CLAUDE.md「スケジュール独断禁止」。本 Q は `scheduled` を空のままとし実施時期の判断を仰ぐ）。決定は DD へ昇格し、RULE-016 対象範囲変更に伴う out-of-graph 著作資産（接続マトリクス・notation・各 author）への伝播を DD の処置に含める。

**指摘時 ref_version**: 傘 SPEC の condition が子の condition 多様性を代表せずミスリード "0.1"（FND-89 サイドカー v0.1.0 時点）／condition 属性なし・語彙外（RULE-016）"0.1"（同 SPEC サイドカー v0.1.0 時点）

**昇格結果（2026-07-06）**: 本 Q は「傘 SPEC は condition を省略し傘ロールを edges から機械判定（傘表現 Q より昇格）」として DD へ昇格・決定済み。決定内容（A 採用・機械判定基準・umbrella/leaf 呼称・不採用理由）は当該 DD に転記した。RULE-016 への傘ロール除外条件の追記・傘 SPEC の残存 condition クリーンアップ・FND-89 の解消・out-of-graph 伝播は当該 DD のフォローアップ（本 PR 未実装・実施時期オーナー判断待ち）とした。
