**深刻度**: WARNING

**対応 Issue**: #283（FND の深刻度語彙・本文必須項目・docs/doc-system の状態表現不一致を解消する）

**指摘**: FND の**状態をどう表現するか**と**本文に何を書くか**を宣言している out-of-graph 文書 4 件が、v2 の確定モデル（status は path から導出・サイドカーに `resolved` キーを持たない）に追随していない。4 件は v2 が持たない状態語 `wontfix`、v2 が受け付けない `resolved: true/false` による機械判定、および path と二重管理になる本文項目 `**対応状況**` を、いずれも現行の指示として提示している。

### 内容（2026-07-27 実測）

#### v2 側の確定モデル（比較の基準）

- `doc-system-v2/config.yml` L31-35 `status_dirs`: `fnd: [open, resolved]`。**`wontfix` は存在しない**。
- 同 L5（ヘッダコメント）: 「FND/Q/DD の status は YAML フィールドではなく **path から導出**（旧 `resolved:` フィールドは廃止）」。
- `doc-system-v2/schema/sidecar.schema.json`: `additionalProperties: false`。許容キーは `title` / `version` / `condition` / `labels` / `scheduled` / `result` / `log_ref` / `carrier` / `edges` の 9 個のみで、**`resolved` は含まれない**（L7-8 および各 property 定義を実測）。
- `doc-system-v2/validate.py` L50-53 `STATUS_DIRS` は config と一致（`fnd: {open, resolved}`）。L591-592 で未知 status を ERROR にする。
- in-graph 担体である PROMPT ノード `verification-author 著作支援プロンプト（TD/TC/TR/VERIFY/FND/DD/Q/PEND）`（v0.2.3）本文 L4 も「FND＝**path status**＋指摘時 ref_version の本文記録＝DD-3」と宣言しており、v2 側は一貫している。

#### 未追随の 4 文書（実測した記述）

| 文書 | 行 | 記述されている内容 | v2 実態との差 |
|---|---|---|---|
| `docs/doc-system/05-verification.md` | L212 | 「**本文**：内容・深刻度（critical/major/minor/info）・**状態（open/resolved/wontfix）**・対処を記載。」 | 状態を本文に書くと指示。かつ `wontfix` は status_dirs に不在 |
| `docs/doc-system/01-document-items.md` | L106 | 「1 検証指摘（内容・深刻度・状態）。**`resolved: true/false`（省略時 false）で機械判定**」／同行末「**`resolved` フィールドで分岐**」 | サイドカーに書けないキーを機械判定の根拠として宣言 |
| `docs/doc-system/07-authoring-guide.md` | L245-249 | 本文 5 項目＝`**深刻度**` / `**内容**` / `**対応状況**` / `**対応内容**` / `**指摘時 ref_version**`。L247 の値域は `[open / resolved / wontfix]` | 項目集合が notation.md と不一致。`対応状況` は path と二重管理。`wontfix` 不在 |
| `docs/doc-system/templates/verification/findings.md` | L25-28 | 本文 4 項目＝`**深刻度**` / `**内容**` / `**対応状況**` / `**対応内容**`。L27 の値域は `[open / resolved / wontfix]` | 同上。加えて `**指摘時 ref_version**` を欠く（DD-3 未反映） |

なお `docs/doc-system/07-authoring-guide.md` L252 は「**対応状況を `resolved` にする場合**、処置対象ノード側に `→ FND-x` の依存辺を追加する」と書いており、`対応状況` を状態の**担い手**として扱っている。単なる重複記載ではなく、状態遷移の起点をこの本文項目に置く手順として記述されている。

#### 本文項目集合の実測比較（3 通りに割れている）

| 宣言の所在 | 項目集合 |
|---|---|
| `doc-system-v2/notation.md` L97 | 指摘 / 深刻度 / 推奨 / 指摘時 ref_version（4） |
| `doc-system-v2/templates/verification/fnd.body.md` | 指摘 / 深刻度 / 推奨 / 指摘時 ref_version（4・notation.md と一致） |
| `docs/doc-system/07-authoring-guide.md` L245-249 | 深刻度 / 内容 / 対応状況 / 対応内容 / 指摘時 ref_version（5） |
| `docs/doc-system/templates/verification/findings.md` L25-28 | 深刻度 / 内容 / 対応状況 / 対応内容（4・ref_version なし） |

v2 側 2 資産と `docs/doc-system` 側 2 資産で**共通する項目は `深刻度` のみ**である。`指摘` と `内容` は名称すら一致しない。

#### 実コーパスの実測

- FND 総数 **128 件**（`fnd/open/` **11 件**・`fnd/resolved/` **117 件**）。
- `^resolved:` を持つサイドカーは **`doc-system-v2/nodes/**` 全体で 0 件**。
- `**対応状況**` を本文に持つのは **116 件**（`fnd/open/` **3/11**・`fnd/resolved/` **113/117**）。
- 本文と path の矛盾は**現時点 0 件**（`fnd/open/` 配下に `**対応状況**: resolved` は 0 件、`fnd/resolved/` 配下に `**対応状況**: open` は 0 件）。
- `wontfix` は `doc-system-v2/` 全体で **1 件のみ**、それも `templates/verification/tr.body.md` L11 の TR 用「**対処**」欄であり、FND の状態語としての使用は **0 件**。

### 根因

v2 移行時に「status を path へ移す」という決定（`config.yml` L5・DD-8 系）が **v2 ツリー内の資産（`config.yml` / `schema` / `validate.py` / `notation.md` / `templates/verification/fnd.body.md`）には反映されたが、`docs/doc-system/` 配下の 4 資産へ伝播しなかった**。CLAUDE.md は `docs/doc-system/` を「機械定義ドキュメント（例外的に正本の一部）」と位置づけており、これらは黙って古くなってよい資産ではない。

伝播が漏れた構造的な理由は、著作エージェントに課された伝播チェック（本 FND を著作した `verification-author` 自身の規約を含む）が **`config.yml` の接続規則（`must_link_to` / `must_be_linked_from`）の変更にしか掛かっていない**ためである。`status_dirs` の確定・`resolved` フィールドの廃止・本文項目ポリシーの変更はいずれも接続規則ではないため、チェックリストを通過してしまう。伝播チェックの対象を接続規則以外へ広げるべきかという論点は、既存の open FND `tmp草案の出力先記述がv1の1親1ファイル形式のまま1ノード2ファイル化に未追随` の末尾（L133）が「別途 Q ノードでの起票を推奨」として既に提起しているため、**本 FND では重複起票しない**。

### 深刻度判定の根拠（実害で判定・2026-07-26 オーナー指示）

**WARNING** と判定する。

**WARNING とする実害（3 点）**

1. **文書化された機械判定手順が、いま実行すると誤答を返す**。`01-document-items.md` L106 は FND の状態を「`resolved: true/false`（省略時 false）で機械判定」と宣言しているが、その手順を実行すると（`^resolved:` の該当 0 件＋「省略時 false」）**128 件すべてが未解消**という結論になる。実際は 117 件が resolved であり、**128 件中 117 件について誤答**する。これは「将来誤りうる」ではなく、現時点で誤った答えを返す手順が正本の一部に記載されている状態である。

2. **正規ツールが本文の状態語を維持しないため、ドリフトの発生が確定している**。`dsv2/reverse.py` の `_append_body_records`（L169-182）は `**指摘時 ref_version**` 行と「付与先なし」行を末尾追記するだけで、**`**対応状況**` 行には一切触れない**（`apply_reverse` L185-199 も `git mv` と 2 ファイルの書き戻しのみ）。現在 `fnd/open/` の 3 件が `**対応状況**: open` を本文に持つため、これらを規定手順（`python3 -m dsv2 reverse --apply`）で解消すると、**path は `fnd/resolved/`・本文は `open`** という矛盾が機械的に生成される。今日の「矛盾 0 件」は手作業で維持されているだけであり、ツールを正しく使うほど壊れる。同型のドリフトは resolved 済み FND `本文-resolved／機械-unresolved-の状態ドリフト-19-件-resolved-true-フラグ欠落・forward-辺残置` として **19 件規模で一度実際に発生している**。

3. **`wontfix` の意思決定が受け皿を失い、未決として誤集計される**。`fnd/wontfix/` を作ると `validate.py` L591-592 が「type 'fnd' の未知 status」で ERROR にし、書き込み方向は fail-close する。したがって「直さないと決めた」指摘は `fnd/open/` に置いたまま本文へ `wontfix` と書く以外に表現手段がなく（4 文書のうち 2 文書がその書き方を明示的に指示している）、その結果 path 由来のあらゆる集計で**未処置として数え続けられる**。オーナーの処置順・スプリント計画の入力が汚染される。

**ERROR にしない理由（実現済みの誤成果物が無い）**

- コーパスに誤った成果物が 1 件も存在しない。`resolved:` キーを持つサイドカー 0 件、本文と path の矛盾 0 件、FND 状態語としての `wontfix` 0 件、未知 status ディレクトリ 0 件。128 件すべてが path 由来モデルに正しく従っている。
- live な RULE 違反はなく、価値経路も遮断されていない。
- 現在進行中の判断が誤った前提の上で行われている事実も確認できない。open FND `tmp草案の出力先記述が…` が ERROR と判定されたのは Issue #160/#255 の判断材料が**現に汚染されている**ためであり、本件にはそれに相当する係属中の汚染がない。

**INFO にしない理由**

- 上記 2 の「規定ツールを使うと矛盾が生成される」は確率的な想定ではなく、コードを読めば確定する挙動である。INFO と判定された先例（FND-103 / FND-105、および同バッチの `resolved FND 4 件の本文に深刻度行がなくテンプレ必須項目を欠く`）は「誤った結果が生まれる経路を持たない被覆・完結性のギャップ」であり、本件は経路が実在する点で類型が異なる。
- 対象が resolved 済みの過去分に閉じておらず、これから著作・解消されるすべての FND に掛かる。

**機械検出可能性を深刻度の根拠にしていないことの明示**（オーナー指示 2026-07-26）: `validate.py` は FND 本文の項目・値を検査せず、`schema/sidecar.schema.json` にも状態に対応するキーがないため、本件由来の誤りは CI で鳴らない。この事実は深刻度を**下げる**根拠として一切用いていない。誤りが長く残存しうる（是正の緊急度を上げる）方向の情報としてのみ記載する。

### 既存 FND との非重複

- 同バッチの `FND 深刻度の語彙が 05-verification.md・v2 テンプレート・実コーパスで三者不一致` は、同じ `05-verification.md` L212 を対象とするが指摘するのは**深刻度の語彙**である。本 FND は同じ行の**状態の語彙**（`open/resolved/wontfix`）を対象とし、指摘している属性が異なる（PR1・もの＋発生源で分ける）。深刻度が決着しても状態表現の不整合は残り、逆も同様。処置箇所が同一行のため実施は同一バッチに載せるのが合理的である。
- 同バッチの `resolved FND 4 件の本文に深刻度行がなくテンプレ必須項目を欠く` は、**既存ノード側の記載漏れ**の指摘。本 FND は**指示側の文書**の指摘であり、対象が逆方向。
- 既存 open FND `tmp草案の出力先記述がv1の1親1ファイル形式のまま1ノード2ファイル化に未追随` は、v1→v2 未追随という同型の事象だが、対象が **in-graph の設計層ノード 3 件（PRS/DS/ORC）と `CLAUDE.md`**、主題が **tmp 草案の出力レイアウト**であり、対象ファイルも主題も重ならない。

### 選択肢（排他）

**選択肢A: 文書側を v2 実態へ合わせる最小同期。**

- `05-verification.md` L212 の「状態（open/resolved/wontfix）」を削除し「状態は path（`fnd/open/`・`fnd/resolved/`）で表す」に置換。
- `01-document-items.md` L106 の `resolved: true/false（省略時 false）で機械判定`・`resolved フィールドで分岐` を「status は path から導出」に置換。
- `07-authoring-guide.md` L245-249 と `templates/verification/findings.md` L25-28 の本文項目を `notation.md` L97 の 4 項目（指摘 / 深刻度 / 推奨 / 指摘時 ref_version）へ統一し、`**対応状況**` を削除。L252 の「対応状況を resolved にする場合」を `dsv2 reverse` 起点の記述へ書き換える。
- 既存 116 件の本文 `**対応状況**` には手を触れない。
- 利点: 誤指示の除去としては最短。既存ノードの改訂が 0 件で、`validate.py` への影響もない。
- 欠点: 116 件に残る `**対応状況**` が「どの規約にも根拠を持たない残置物」になる。上記実害 2（`dsv2 reverse` が維持しないことによるドリフト確定）は**解消しない**——open 3 件は依然として矛盾を生む。`wontfix` の受け皿も未定のまま。

**選択肢B: A ＋ `**対応状況**` を本文項目として正式に廃止し、既存 116 件から状態語を除去する。**

- A の文書同期に加え、116 件の `**対応状況**` 行を処理する。ただし**単純削除はできない**——実測では大半が `**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-53-1/53-2/53-3）` のように**処置内容・処置日・処置先を併記**しており、行ごと消すと「いつ・どう直したか」の記録が失われる（PR8・消さない）。状態語だけを落とし、括弧内の処置記録を `**処置**` 等の別項目へ退避させる変換が要る。
- 利点: 状態の担い手が path 1 本になり、二重管理が構造的に消える（PR2）。実害 2 のドリフト経路が根絶される。`dsv2 reverse` への改修も不要。
- 欠点: 116 件の一括編集を伴い、変換規則の設計（括弧内テキストの退避先・退避形式）と z バンプの扱いを決める必要がある。作業面積が最大。

**選択肢C: A ＋ `**対応状況**` を存置し、`dsv2 reverse` に本文の状態語を書き換えさせる。**

- `notation.md` L97 の FND 本文項目に `対応状況` を正式に追加し（＝ v2 側を `07-authoring-guide` 側へ寄せる）、`dsv2/reverse.py` の `_append_body_records` を拡張して `git mv` と同時に本文の状態語を `open` → `resolved` へ書き換える。
- 利点: 既存 116 件を編集せずに実害 2 を止められる。処置内容の併記という運用上有用な情報がそのまま残る。
- 欠点: **二重管理そのものは残る**（PR2 に反する）。`dsv2 reverse` を経由しない手作業の `git mv` では依然ずれる。`**対応状況**` を持たない 12 件との不均一も残る。加えて「path が唯一の状態表現」という確定済みモデルを本文へ部分的に戻すことになり、`config.yml` L5 の決定と緊張する。

**選択肢D: 文書ではなくモデル側を文書へ寄せる。**

- `status_dirs` に `wontfix` を追加し（`config.yml` L31-35＋`validate.py` L50-53＋`FORMAT.md`）、サイドカーに `resolved` キーを復活させる（`schema/sidecar.schema.json`）。
- 欠点: `resolved` フィールドの廃止と path 由来 status は `config.yml` L5 に明記された**確定済みの決定**であり、これを覆すのは FND の是正処置ではなく新たな DD を要する意思決定である。FND の処置として独断で行うことはできない。

### 推奨（決定ではない・決定はオーナー）

**B を採る。ただし第 1 段として A の文書同期のみ先行実施し、第 2 段で 116 件の変換を行う。`wontfix` の可否は A に含めずオーナー決定へ切り出す。C は B が採れない場合の次善。D は非推奨。** 根拠は 4 点。

1. **A だけでは主たる実害が残る**。実害 2（`dsv2 reverse` が本文状態語を維持しないためのドリフト確定）は文書の文言を直しても消えない。`fnd/open/` の 3 件は依然として、規定ツールで解消した瞬間に矛盾を生む。A を終点にすると「文書は正しくなったがコーパスは壊れ続ける」状態になる。
2. **B と C の分岐点は PR2（二重管理の回避）である**。同じ事実（FND の状態）を path と本文の 2 箇所で保持し続ける限り、片方だけを更新する経路が残る。C はその経路を `dsv2 reverse` に限って塞ぐだけで、手作業の `git mv` や新規著作時の書き忘れは塞げない。実際に v1 期には同型のドリフトが 19 件規模で発生している。B は保持箇所を 1 つにするため、経路自体が存在しなくなる。
3. **段階実施でブロッキングを避けられる**。A の文書同期は判断の余地が小さく（v2 側 5 資産が一貫しており、コーパス 128 件が例外なくそれに従っている＝文書側が誤であることが実測で確定している）、即時実行できる。116 件の変換規則設計は独立に進められるため、第 1 段の完了を待たせない。ただし **B の第 2 段が完了するまで本 FND を resolved にしない**ことで、切り出した処置の忘却を防ぐ。
4. **`wontfix` を A に紛れ込ませて消してはならない**。`wontfix` を status_dirs から外すという決定は `doc-system-v2/` のどこにも記録がなく（DD ノード・config.yml いずれにも `wontfix` の言及なし＝実測）、単に存在しないだけである。文書から `wontfix` を削除する行為は「直さないと決めた指摘を表現する手段を持たない」という運用上の制約を**決定として確定させる**ことに等しい。これは AI が文言整理のついでに行ってよい判断ではない（PR7・独断禁止）。オーナーに対し「(a) `wontfix` を status_dirs に新設する／(b) 表現手段を持たないことを明示的に決定し文書から削除する／(c) `fnd/resolved/` に置き本文で `wontfix` 理由を記す運用にする」の 3 案を提示して決定を仰ぐ。

処置要否・実施時期の決定はオーナーが行う。本 FND では起票側で「対応不要」の結論を出さない（PR7・独断禁止）。

### スコープ外だが処置時に同一箇所で目に入る事実（本 FND の指摘には含めない）

`05-verification.md` L202-210 の FND 例示は `id: FND-001` / `type: FND` を含み、`templates/verification/findings.md` L8-22 は `⬡ FND-001 · v0.1` バッジと `id` / `type` を含む YAML ブロックを持つ。v2 のサイドカーは `id` / `type` を持たない（path と stem から導出）。これは**サイドカーキーの陳腐化**であって本 FND のアサーション（状態表現と本文項目）とは別命題であるため指摘に含めない。ただし A/B のいずれでも同一ブロックを編集するため、処置時に併せて確認できるよう所在のみ記録する。

### config.yml 接続規則変更チェック（FND-99 パターン）

本 FND の処置は `doc-system-v2/config.yml` の `must_link_to` / `must_be_linked_from` / `must_not_link_to` / `fnd_lifecycle` のいずれも追加・変更・削除しない（変更対象は文書の文言、および選択肢により本文項目ポリシーと `status_dirs`）。したがって接続規則変更に伴う伝播チェック（`docs/doc-system/03-connection-matrix.md`・`docs/doc-system/01-document-items.md`・各 author エージェント／スキル）は**不要**である。FND-104 / FND-105 が RULE 台帳・属性検査ルールの操作を接続規則変更でないと判定した先例と同じ扱い。

ただし選択肢D は `status_dirs` の変更を伴い、`config.yml` と `validate.py` L50-53 の直書き集合、`FORMAT.md` の §status 遷移が同期対象になる（接続規則ではないため上記チェックリストの対象外である点が、まさに本 FND の根因である）。

### 状態と辺についての注記

本ノードの状態は path（`04-verification/fnd/open/`）から導出される（サイドカーに `status` / `resolved` を持たない）。open のため `fnd_lifecycle.unresolved.must_link_to` に従い forward 辺 1 本を持つ。

被指摘の実体 4 件はいずれも `docs/doc-system/` 配下の out-of-graph 資産（ノード ID・版を持たない・DD-8 / FND-104）であり forward 辺を張れない。そこで in-graph の担体として、FND の著作規約を保持し本文 L4 で「FND＝path status」と宣言している PROMPT ノード `verification-author 著作支援プロンプト（TD/TC/TR/VERIFY/FND/DD/Q/PEND）` を指摘対象とする（FND-99 が out-of-graph 著作資産の指摘を PROMPT ノードで在グラフ化した先例に従う）。なお当該 PROMPT ノード自身は状態表現について正しい記述を持つが、**FND 本文の項目集合を一切宣言していない**ため、項目集合の正本が out-of-graph にしか存在しないという構造の一端を担っている。

`dsv2/reverse.py`・`doc-system-v2/validate.py`・`doc-system-v2/config.yml`・`doc-system-v2/schema/sidecar.schema.json` は実測の根拠として参照したが、いずれも本 FND の指摘対象ではない（v2 実態の側＝正しい側）ため辺は張らない。

**指摘時 ref_version**: `verification-author-著作支援プロンプト-td-tc-tr-verify-fnd-dd-q-pend` "0.2"（同 `.yaml` v0.2.3 時点）。被指摘の実体である `docs/doc-system/05-verification.md`（L212）・`docs/doc-system/01-document-items.md`（L106）・`docs/doc-system/07-authoring-guide.md`（L245-249・L247・L252）・`docs/doc-system/templates/verification/findings.md`（L25-28）は out-of-graph（版なし）であり forward 辺を張れないため、所在を行番号で本文に記録するに留める。解消時も `dsv2 reverse` はこれら 4 文書に backref を付与できないため、**4 文書の訂正完了は本 FND 本文への追記で証跡を残すこと**。

### 改訂履歴

#### v0.1.1（2026-07-30）— 対応 Issue の採番を反映（本文のみ・辺と `edges[].ref_version` は不変）

- 冒頭 `**深刻度**` 行の直後に `**対応 Issue**: #283（FND の深刻度語彙・本文必須項目・docs/doc-system の状態表現不一致を解消する）` を追記した。Issue #283 は本 FND を含む 3 FND ＋ 1 Q を束ねた対応 Issue であり、Issue #263（[Phase 1] 陳腐化・起票漏れの解消）アイテム2・F-d の処置として採番された。
- **指摘・深刻度・選択肢・推奨は一切変更していない**（起票時の判断記録を保全する・PR8）。
- **版バンプ**: DD-8 §4 に照らし **z バンプ（0.1.0 → 0.1.1）**。変更は本文のみで、YAML キーの追加・型変更・辺の追加/削除/変更を伴わない（`edges` 1 本と `ref_version` "0.2" は不変）。z バンプのため依存元ノードの `ref_version` 更新（伝播）も不要（本ノードを参照する依存元は現時点で存在しない）。
