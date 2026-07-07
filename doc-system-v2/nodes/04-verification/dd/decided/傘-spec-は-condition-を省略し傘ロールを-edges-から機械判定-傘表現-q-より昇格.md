**status: decided**（2026-07-06 オーナー承認）

> **辺の扱い**: 本 DD は `edges: []` にせず、フォローアップ対象へ義務辺 `DD→RULE-016 SPEC` を1本張る。RULE-016 への「傘ロール除外条件」の追記は本 PR では実装せず follow-up とするため、`DD→X` の残存を「未反映」シグナル（decision_spine／RULE-001）として意図的に可視化する。昇格元 Q からは `Q→この DD` の張り返しで被参照が確保される（RULE-005 完全孤立を回避）。

**論点**（傘・非テスタブルノードの condition 表現を明示マーカー化するか省略維持か より昇格・要約）: 傘（アンブレラ）ノード・非テスタブルノードの condition をどう表現するか。現状は「傘ノードは condition を省略する」方式（Sub-A 採用・#81 で umbrella は condition 値でなくなった）で運用している。これで十分か、明示マーカーや別属性が要るか。本決定により既存 FND-89（傘 SPEC の condition が子の多様性を代表せずミスリード）の解消方針が確定する。

**現状**:
- `config.yml` の condition_vocab は `[normal, boundary, empty, failure, error]` の5語。「非テスタブル(傘)ノードは condition を持たない」とコメントに明記され、傘は condition 省略で表す。slugify.py も umbrella マーカーを condition 語彙から外し、傘＝condition 不在で一貫している。
- 一方 RULE-016 は「SPEC/TD に condition 属性がない、または語彙外の値」を ERROR 報告する。傘 SPEC が condition を省略すると RULE-016 と衝突しない前提（傘は対象外）が config コメント・notation の散文にのみ存在し、機械可読な区別が無い。
- FND-89 の指摘: アンブレラ SPEC-44（condition: normal）の子は normal / boundary / error と多様で、傘の condition が normal 固定だと子の多様性を代表せずミスリードを招く。傘から condition を外すと RULE-016 に抵触するジレンマ。傘 SPEC に `condition` が残存する箇所があり「傘＝省略」への統一が未徹底。

**選択肢**:
- **A（省略維持＋傘を RULE-016 対象外と規約で明文化）** — 現行「傘は condition 省略」を維持し、RULE-016 の検査対象から傘ノードを機械判定で除外する基準を明文化する。トレードオフ＝「傘か否か」の機械判定基準の新設が必要。
- **B（明示マーカー導入・専用 condition 値 `mixed`/`umbrella`）** — 傘に専用 condition 値を持たせ RULE-016 を満たす。トレードオフ＝等価分割クラスでない値が vocab に混じり5値の意味が濁る。RULE-019・coverage_rules の再定義も要る。
- **C（別属性導入・`testable: false` フラグ新設）** — condition と別のブール属性で傘を表す。RULE-016 は `testable: false` を対象外に。トレードオフ＝サイドカーのキーが増える（未知キー禁止の schema 変更が必要）。

**推奨**（起票時）: **A（省略維持＋傘の機械判定基準を明文化）を第一候補**、**C を次点**。理由＝(1) 現行が既に「傘＝省略」で運用実績があり破壊的変更が最小、(2) B は等価分割でない値を vocab に混ぜ論点2/4 の整合を複雑化、(3) A の弱点（傘判定基準未定義）は C で補える。いずれもオーナー判断。

**決定**: オーナー回答（2026-07-06）「別属性で子ノードを持ってるかどうかを判定。testable 以外の名前を検討して」に基づき、**選択肢 A（省略維持＋傘の機械判定基準の明文化）を採用**する。確定事項は以下。
- **機械判定基準**: 「**同型の子から親向き依存辺で被参照される SPEC ＝ 傘**」とする。ある SPEC が別の SPEC から `SPEC→SPEC`（子→親 refines）辺の `to` に指されている（＝同型の被依存辺を持つ）なら傘。meta.json / edges から決定論的に導出でき、格納属性を増やさない。**RULE-016 はこの傘ロールのノードを検査対象外**にする（傘は condition を持たない）。
- **呼称**: 「**umbrella（傘）/ leaf（葉）**」を採用。本コードベースで既に「傘/umbrella」が正準語彙（FORMAT.md・config コメント・FND-89）であり、追加語彙を導入せず最も自然。傘は格納値でなく **edges から導出されるロール**であることを config/notation に明文化する。
- **不採用**: B（専用 condition 値）は等価分割 vocab を濁すため不採用。C（`testable: false` 等の格納属性新設）はオーナーが求める「構造からの判定」ではなく新規キーを増やす（schema 未知キー禁止に抵触）ため不採用。

**根拠**: オーナー指示は condition とは別の情報（サイドカーの `edges` という既存構造）を見て傘性を機械判定せよという要請であり、FORMAT.md（L76）の既定原則「傘性は『同型の子から被参照される』構造から導出する（condition に umbrella を混ぜない）」の追認・具体化である。edges 由来の導出は格納属性を増やさず、schema 未知キー禁止・等価分割 vocab の純度をともに守れる。A 採用により vocab（論点2）・RULE-019 への波及はなく、影響は「RULE-016 に傘ロール除外条件を追加する」1 点に限定される。

**接続規則変更チェック（FND-99 パターン）**: 本決定は `doc-system-v2/config.yml` の接続規則（`must_link_to` / `must_be_linked_from`）自体の追加・変更・削除を**含まない**。変更対象は RULE-016（condition 属性検査）の検査対象範囲であり、ノード間の必須接続関係ではない。したがって接続マトリクス・ドキュメント一覧・各 author への接続規則伝播は不要。ただし「傘ロールは edges 由来で機械判定・RULE-016 対象外・condition 省略」という運用規約の明文化は out-of-graph 資産（config.yml コメント・notation・関連 author）へ伝播する必要があり、これは下記フォローアップに含める（本 PR では未実施）。

**影響範囲**:
- **in-graph（本 PR reconciliation で反映完了）**: 本 DD ノードの新規著作と、昇格元 Q（傘・非テスタブルノードの condition 表現…）の `q/open`→`q/closed` 移動・張り返し辺付与・status 更新。
- **本 PR では実装しないフォローアップ（follow-up・黙って先送りしない）**:
  1. `RULE-016` SPEC（`condition-属性なし・語彙外-rule-016`）本文への「傘ロール（同型の子→親辺の target になっている非葉 SPEC）は検査対象外」という除外条件の追記。
  2. 傘 SPEC の残存 `condition` 値のクリーンアップ（例: 傘 SPEC「存在しない ID への参照」＝`condition: error` → 省略、FND-89 が指す SPEC-44 相当ノードの `condition: normal` → 省略）。
  3. **FND-89 の解消**（`04-verification/fnd/open/傘-spec-の-condition-が子の-condition-多様性を代表せずミスリード`）。本 PR では触らず open のまま残す。解消時は `dsv2 reverse` で辺逆転（機械実行）。
  4. out-of-graph 資産（config.yml コメント・notation・接続マトリクス・各 author）への「傘ロールは edges 由来判定・RULE-016 対象外・condition 省略」の明文化伝播。
  - **実施時期はオーナー判断待ち**。本 PR は決定の記録（この DD ノードの著作）のみとし、上記1〜4 の実装は独断で先送り・独断で今スプリント実施のいずれもしない（CLAUDE.md スケジュール独断禁止・透明性規律）。義務辺 `DD→RULE-016 SPEC` が残存することで未反映が RULE-001 により可視化される。

**覆る場合の影響範囲**: 本決定が覆り B/C を採る場合、(1) condition_vocab または schema（サイドカー許可キー）の変更、(2) RULE-016・RULE-019・coverage_rules の再定義、(3) slugify.py の condition マーカー扱い、(4) FND-89 の解消方針の再検討、が戻し対象となる。傘の機械判定を edges 由来から格納属性へ切り替える場合は既存傘 SPEC 全件への属性付与が必要。
