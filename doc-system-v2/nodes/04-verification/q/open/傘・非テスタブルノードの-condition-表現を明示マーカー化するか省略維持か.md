**status: open**

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

**推奨**: **A（省略維持＋傘の機械判定基準を明文化）を第一候補**、**C（別属性）を次点**。理由：(1) 現行は既に「傘＝省略」で運用実績があり、破壊的変更が最小。(2) B は等価分割クラスでない値を vocab に混ぜ、論点2/4 の整合を複雑化するため非推奨。(3) A の弱点（傘の機械判定基準が未定義）は、C（明示 `testable: false`）で補える。A で基準を明文化しきれない場合は C へ。**いずれもオーナー判断**。

**論点4（整合連動）への波及**: 本決定は RULE-016（condition 必須検査）の対象範囲に直接影響する。B/C を選ぶ場合は RULE-019・coverage_rules との整合を論点4 で合わせて確定する必要がある。

**他論点との結合**: 本 Q（論点1）は論点2（5値セット）・論点3（always_error）と condition 語彙という同一主題を共有するが、傘表現は「テスタブル/非テスタブルの区別」という独立した決定軸のため別 Q として起票した（1論点1Q・Issue #78 の4点に1:1対応）。B を選ぶと論点2 の vocab セットに値が増えるため、その場合のみ論点2 と統合判断する。

**ブロッカー**: 傘 condition の表現方式は**オーナー判断**。実施時期（今スプリント vs 次スプリント以降）も含めてオーナーが決定する（**独断でのスプリント繰越は禁止**＝CLAUDE.md「スケジュール独断禁止」。本 Q は `scheduled` を空のままとし判断を仰ぐ）。決定後は DD へ昇格し、決定が接続規則（RULE-016 対象範囲）を変える場合は out-of-graph 著作資産（接続マトリクス・各 author）への伝播を DD の処置に含める。

**指摘時 ref_version**: 傘 SPEC の condition が子の condition 多様性を代表せずミスリード "0.1"（FND-89 サイドカー v0.1.0 時点）／condition 属性なし・語彙外（RULE-016）"0.1"（同 SPEC サイドカー v0.1.0 時点）
