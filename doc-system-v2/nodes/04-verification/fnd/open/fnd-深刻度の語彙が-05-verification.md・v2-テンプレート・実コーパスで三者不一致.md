**深刻度**: WARNING

**対応 Issue**: #283（FND の深刻度語彙・本文必須項目・docs/doc-system の状態表現不一致を解消する）

**指摘**: FND 本文の `**深刻度**` 欄に書くべき語彙が著作資産のあいだで三通りに宣言されており、そのうち 2 つが実コーパス（FND 128 件）の実態と一致しない。テンプレートをそのまま埋めた著作が非適合値を出力する経路が正規手順上に開いている。

### 内容（2026-07-27 実測）

深刻度の語彙を宣言している資産と、その宣言内容の実測結果は次のとおり。

| 宣言の所在 | 宣言している語彙 | 実コーパスとの一致 |
|---|---|---|
| `docs/doc-system/05-verification.md` L212 | `critical / major / minor / info` | **不一致**（4 語すべて実使用 0 件） |
| `doc-system-v2/templates/verification/fnd.body.md` L3 | `[low / medium / high（または ERROR / WARNING / INFO）]` | **主たる語彙が不一致**（`low/medium/high` は実使用 0 件） |
| `docs/doc-system/07-authoring-guide.md` L245 | `[ERROR / WARNING / INFO]` | 一致 |
| `docs/doc-system/templates/verification/findings.md` L25 | `[ERROR / WARNING / INFO]` | 一致 |
| `doc-system-v2/notation.md` L97 | 項目名（`FND: 指摘 / 深刻度 / 推奨 / 指摘時 ref_version`）を列挙するのみで語彙を宣言しない | 判定対象外 |

実コーパス（`doc-system-v2/nodes/04-verification/fnd/**`）の実測：

- FND 総数 **128 件**（`fnd/open/` 11 件・`fnd/resolved/` 117 件）。
- `**深刻度**` 行を持つのは **124 件**（resolved 113・open 11）。その内訳は **ERROR 22**（resolved 13・open 9）／**WARNING 82**（resolved 80・open 2）／**INFO 20**（resolved 20・open 0）＝ **124 件すべてが `ERROR / WARNING / INFO`**。
- `**深刻度**: critical|major|minor` は **0 件**、`**深刻度**: low|medium|high` も **0 件**（`doc-system-v2/` 全体に対する grep 実測）。
- 残る 4 件は `**深刻度**` 行そのものを持たない（別 FND「resolved FND 4 件の本文に深刻度行がなくテンプレ必須項目を欠く」として同時起票）。

つまり **実コーパスは 124/124 で単一語彙に収束しているのに、それを指示すべき文書側が 3 通りに割れている**。しかも本 FND の指摘対象である in-graph 担体（`verification-author 著作支援プロンプト` ノード・v0.2.3）は本文に「深刻度」の語を一切持たず、**語彙は out-of-graph 資産にのみ分散して存在する**。版を持つ担体が語彙を保持していないため、どの宣言が正なのかを版で追跡することもできない（CLAUDE.md「依存仕様の参照原則」＝out-of-graph を唯一の根拠にしない、に反する状態）。

### 深刻度判定の根拠（実害で判定・2026-07-26 オーナー指示）

**WARNING** と判定する。

- **ERROR にしない理由 — 実現済みの実害はゼロ**。124 件すべてが適合語彙を使っており、誤った語彙で書かれたノードは 1 件も存在しない。live な RULE 違反もなく、価値経路も遮断されていない。
- **INFO にしない理由 — 失敗経路が正規手順のど真ん中にある**。`doc-system-v2/templates/verification/fnd.body.md` は v2 コーパス自身のテンプレートであり、v2 の FND を著作する者が最初に複製する資産である。そこでは `low / medium / high` が**主たる**語彙として置かれ、`ERROR / WARNING / INFO` は括弧内の代替として併記されているにすぎない。テンプレートを素直に埋めれば非適合値が出る。`05-verification.md` L212 を根拠にした著作者は `major` 等を書く。これは被覆・均一性のギャップ（FND-103/105 が INFO とされた類型＝検出が落ちる経路を持たない）ではなく、**文書の指示に literal に従うと誤った成果物が出る**類型であり、FND-99（決定の out-of-graph 未伝播で旧ルールの辺を再生産）・FND-104・FND-106 が WARNING と判定された類型と同じである。
- **誤りが入っても検出されない**。深刻度はサイドカーのキーではなく本文テキストであり、`doc-system-v2/schema/sidecar.schema.json` に `severity`／深刻度に対応するキーは存在しない（grep 実測 0 件）。`doc-system-v2/validate.py` にも FND 本文の項目・値を検査する処理はない（同 0 件）。非適合値が混入しても `validate.py` / CI は鳴らず、人間が読んで気づくまで残る。
- **実害が現れるのはオーナーの意思決定**。深刻度は機械消費されず、トリアージ・処置順・スプリント計画の入力である。語彙が割れれば 128 件の母集団に対する集計・優先順位付けが成立しなくなる。これは現に係属中の Q「深刻度の判定基準是正を既存 FND 全件へ遡及適用するか」が必要とする入力そのものであり、放置すれば Q の決定基盤を後から侵食する。

### 係属中の Q との関係（重複ではない）

Q「深刻度の判定基準是正を既存 FND 全件へ遡及適用するか」は **どういう場合にどの値を選ぶか＝判定基準**の論点である。本 FND は **選べる値の集合＝語彙**が資産間で割れているという別の事実の指摘であり、対象が異なる（PR1・もの＋発生源で分ける）。Q が基準を確定しても語彙の不一致は残り、逆に語彙を統一しても基準は決まらない。ただし処置先の資産が重なる（両者とも `05-verification.md` と著作資産に手を入れる）ため、実施は同一バッチに載せるのが合理的である。

### 選択肢（排他）

**選択肢A: 語彙を `ERROR / WARNING / INFO` に一本化し、非適合な 2 資産を同期する。**

- `docs/doc-system/05-verification.md` L212 の `critical/major/minor/info` を `ERROR/WARNING/INFO` へ書き換える。
- `doc-system-v2/templates/verification/fnd.body.md` L3 の `[low / medium / high（または ERROR / WARNING / INFO）]` を `[ERROR / WARNING / INFO]` へ書き換える（併記をやめ単一語彙にする）。
- 利点: 実コーパス 124 件・`07-authoring-guide.md`・`findings.md` が既に採用している語彙へ文書側を寄せるだけで、**既存ノードの改訂は 1 件も発生しない**。実測で「コーパスが正・文書が誤」の関係が確定しているため判断の余地が小さい。
- 欠点: 語彙の正本が依然 out-of-graph（版を持たない資産）に留まるため、同型のドリフトが再発しうる。

**選択肢B: A に加えて、語彙の正本を in-graph に置く。**

- 指摘対象の PROMPT ノード（`verification-author 著作支援プロンプト`・v0.2.3）本文に語彙を明記し、`doc-system-v2/notation.md` L97 の FND 本文項目列挙にも語彙を併記する。out-of-graph 資産はそこを参照する形にする。
- 利点: 版付きの担体が語彙を保持するため以後の変更を版で追跡でき、本 FND と同型の再発が構造的に止まる。CLAUDE.md「依存仕様の参照原則」（版なし out-of-graph を唯一の根拠にしない）とも整合する。
- 欠点: PROMPT ノードの MINOR バンプと、4 ツリー資産（`.claude/` / `.github/` / `.codex/` / `.agents/`）への反映が伴う。作業面積は A より大きい。

**選択肢C: 語彙自体を再設計する。**

- 係属中の Q で「実害で判定する」基準が確定するのに合わせ、語彙も基準を反映した体系（実害の有無・発現時期を表す語など）へ刷新する。
- 欠点: 既存 124 件の値をすべて新語彙へ読み替える必要が生じ、Q の選択肢①（全件遡及）と同等のコストが発生する。加えて Q が未決のまま語彙を動かすと**基準と語彙の 2 変数を同時に動かす**ことになり、分布の変化がどちらに起因するのか追跡できなくなる。

**推奨（決定ではない・決定はオーナー）**: **A を即時実施し、B を Q の決定と同一バッチで実施する。C は非推奨。** 根拠は 3 点。

1. **A は判断の余地が小さく副作用がない**。実測で 124/124 が既に `ERROR/WARNING/INFO` に収束しており、A は文書を実態へ合わせるだけでノードの改訂も再判定も発生しない。
2. **A だけでは再発が止まらないので B を分離しない**。A 後も語彙の正本は版なし資産に残り、本 FND と同型のドリフトが再び起きうる。B は Q の決定でも触る資産（著作エージェント・4 ツリー）と重なるため、同一バッチに載せて重複作業を避けるのが合理的。
3. **C は Q が未決である限り採らない**。基準と語彙を同時に動かすと既存 124 件の読み替えコストが発生し、かつ変化の要因が追跡不能になる。Q が「語彙も変える」と決めた場合にのみ再検討する。

処置要否・実施時期の決定はオーナーが行う。本 FND では起票側で「対応不要」の結論を出さない（PR7・独断禁止）。

### config.yml 接続規則変更チェック（FND-99 パターン）

本 FND は FND 本文の 1 項目の**語彙**に関する指摘であり、`doc-system-v2/config.yml` の `must_link_to` / `must_be_linked_from` / `must_not_link_to` / `fnd_lifecycle` のいずれも追加・変更・削除しない。よって接続規則の著作資産への伝播チェック（接続マトリクス `docs/doc-system/03-connection-matrix.md`・ドキュメント一覧 `docs/doc-system/01-document-items.md`・各 author エージェント／スキル）は**不要**である（変更される接続規則型が存在しないため伝播対象なし。FND-104/105/106 が RULE 台帳・トリガ宣言の操作を接続規則変更でないと判定した先例と同じ）。

なお選択肢A/B を採る場合の同期先は接続規則ではなく**語彙の記述**であり、対象は上表に列挙した 5 資産、および B を採る場合は PROMPT ノードと 4 ツリー資産（整合は `python3 -m asset_parity check` で確認する）。

### 状態と辺についての注記

本ノードの状態は path（`04-verification/fnd/open/`）から導出される（サイドカーに `status` / `resolved` を持たない）。open のため `fnd_lifecycle.unresolved.must_link_to` に従い forward 辺 1 本を持つ。被指摘の実体は out-of-graph 資産（下記）でノード ID を持たず forward 辺を張れないため、in-graph の担体として、FND 著作規約を保持しながら語彙を宣言していない `verification-author 著作支援プロンプト` ノードを指摘対象とする（FND-99 が out-of-graph 著作資産の指摘を PROMPT ノードで在グラフ化した先例に従う）。

**指摘時 ref_version**: `verification-author-著作支援プロンプト-td-tc-tr-verify-fnd-dd-q-pend` "0.2"（同 `.yaml` v0.2.3 時点）。被指摘の実体である `docs/doc-system/05-verification.md`（L212）・`doc-system-v2/templates/verification/fnd.body.md`（L3）・`docs/doc-system/07-authoring-guide.md`（L245）・`docs/doc-system/templates/verification/findings.md`（L25）・`doc-system-v2/notation.md`（L97）はいずれも out-of-graph（ノード ID・版を持たない・DD-8/FND-104）であり forward 辺を張れないため、所在を行番号で本文に記録するに留める（FND-99/103/104/106 が out-of-graph 資産を本文参照に留めた先例と同じ扱い）。

### 改訂履歴

#### v0.1.1（2026-07-30）— 対応 Issue の採番を反映（本文のみ・辺と `edges[].ref_version` は不変）

- 冒頭 `**深刻度**` 行の直後に `**対応 Issue**: #283（FND の深刻度語彙・本文必須項目・docs/doc-system の状態表現不一致を解消する）` を追記した。Issue #283 は本 FND を含む 3 FND ＋ 1 Q を束ねた対応 Issue であり、Issue #263（[Phase 1] 陳腐化・起票漏れの解消）アイテム2・F-d の処置として採番された。
- **指摘・深刻度・選択肢・推奨は一切変更していない**（起票時の判断記録を保全する・PR8）。
- **版バンプ**: DD-8 §4 に照らし **z バンプ（0.1.0 → 0.1.1）**。変更は本文のみで、YAML キーの追加・型変更・辺の追加/削除/変更を伴わない（`edges` 1 本と `ref_version` "0.2" は不変）。z バンプのため依存元ノードの `ref_version` 更新（伝播）も不要（本ノードを参照する依存元は現時点で存在しない）。
