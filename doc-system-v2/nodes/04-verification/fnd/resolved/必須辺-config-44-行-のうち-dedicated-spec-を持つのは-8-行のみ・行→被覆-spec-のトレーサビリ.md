**深刻度**: INFO

**改訂理由（z バンプ v0.2.0→v0.2.1・FND-111 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠・DD-21 確定）**:
FND-111（resolved-flag ドリフト 19 件一括是正）に伴い辺逆転を完了。元 forward 辺（`→SPEC-8 "0.2"`・`→FND-79 "0.1"`）を削除し `edges: []`・`resolved: true` を付与。処置対象 SPEC-8 から `→FND-102` の backward 辺を受ける（backref 付与）。FND-79 は provenance（FND→FND・FND-79 は open・本文記録のみ・backref なし）。指摘時 ref_version は本文に記録（DD-3）。

**根拠（深刻度確定の理由）**: issue #30 の点検の結論として **完全な起票漏れ（挙動を規定する SPEC の不在）は存在しない**。必須辺の機械判定 RULE-006 の挙動は SPEC-8「必須上流辺の欠如」（condition: failure・親 FR-3）が parametric な傘仕様として config 44 行すべてを一般則でカバーしており、ツール挙動は定義済み（ERROR ではない）。残る課題は「dedicated（テスタブル）SPEC への昇格基準が未文書化」「config 行→被覆 SPEC のトレーサビリティ表が不在」というドキュメント整備・テスト被覆の均一化の論点であり、現時点の実害はゼロ。同根の既存指摘 **FND-79（open・INFO「RULE-006/025/026 が複数 SPEC に分散→索引化」）** と性質が一致するため、決定の一貫性を保つ意味でも INFO に揃える。なお「将来 config 行を追加した際に SPEC 追従漏れを機械検知できない」リスクは WARNING 寄りだが、これは現状の欠陥ではなく将来の運用機構の話であり、INFO の推奨（トレーサビリティ表・昇格基準の明文化）で吸収できると判断した。

**対応状況**: resolved（2026-06-21・オーナー決定＝選択肢②「全 44 行を dedicated SPEC 化」を実施）

**対応内容**: 必須辺 config 44 行のうち dedicated SPEC を欠いていた 36 行に対し、行固有・テスタブルな子 SPEC（各 condition: failure〔SPEC-28-3 のみ normal・post-mvp〕・「当該 node が必須辺を欠くとき RULE-006 を config 行の severity で報告」を単一アサーション化）を新設した。内訳：

- **SPEC-56**（傘・親 FR-3）＋ SPEC-56-1〜8（要件層 8 行：SR→VAL／FR→SR／NFR→SR／SPEC→[FR,NFR,SPEC]／VAL←[SR]／SR←[FR,NFR,ACTOR]／FR←[SPEC]／NFR←[SPEC]）
- **SPEC-57**（傘・親 FR-3）＋ SPEC-57-1〜12（分析層 残 12 行：ACTOR→SR／TERM→SPEC／I→SPEC／O→SPEC／O→ACTOR／D→SPEC／D→P／P→SPEC／E→SPEC／E→ACTOR／ACTOR←[E,I,O]／D←[P]。価値経路 3 種 O→P・I←P・E←P は既存 SPEC-30 が担う）
- **SPEC-58**（傘・親 FR-3）＋ SPEC-58-1〜12（設計層 12 行：ORC→E／DS→P／MOD→[P,D]／DM→TERM／DM→MOD／PORT→MOD／PRS→DS／SCM→SPEC／CFG→SCM／CFG→SPEC／PROMPT→SPEC／E←[ORC]）
- **SPEC-18-6〜8**（既存傘 SPEC-18 を拡張・検証層 3 行：TD→SPEC／TR→TC／TD←[TC]）
- **SPEC-28-3**（既存傘 SPEC-28 を拡張・実装層 1 行・post-mvp：SRC→[DM,PORT,ORC]）

これで 44 行すべてが dedicated SPEC を持ち（既存 8 行＝SPEC-30-1/2/3・SPEC-15-1・SPEC-18-2/3/4/5 ＋ 新設 36）、各 SPEC 本文の `入力/トリガ` に対応 config 行を明記したため「config 行→被覆 SPEC」のトレーサビリティが 1:1 で成立した（昇格基準の論点も全行昇格により解消）。一般則 SPEC-8 は parametric な傘仕様として併存し、新設子はその個別ケースの位置づけ。（PR #34 レビュー対応：origin/main マージで config が fnd_lifecycle 版＝標準 44 行に更新されたため、当初の 45 行/既存 9 の計数を 44 行/既存 8 へ訂正。FND→any は `must_link_to` から `fnd_lifecycle.unresolved.must_link_to` へ移動し標準 44 行の対象外となった。）

**バックリファレンス**: 処置の中心である新設傘 SPEC-56／SPEC-57／SPEC-58 に `→FND-102` 辺を付与済み（検証層 SPEC-18-6〜8・実装層 SPEC-28-3 は既存傘の拡張のため、代表 backref は本 3 傘が担い、本文で全 36 子を列挙）。**forward 辺（→SPEC-8／→FND-79）は baseline 慣行どおり保持**し、辺逆転（resolved FND の forward 削除）は FND-101／Q-4 の決定に依存する別ブランチ処置の対象として同一コホートに属する。

> **残課題（別件）**: 形式的な「config 行→SPEC」索引表（人間可読の一覧）は FND-79（RULE-006/025/026 の分散→索引化・open・INFO）の領分として別途検討。本 ② 実施で RULE-006 の dedicated SPEC はさらに増えたため、FND-79 の索引化要望はむしろ強まる（FND-79 のクローズはオーナー判断）。

**指摘時 ref_version**: SPEC-8 "0.2"（doc-system/04-verification 配下 SPEC-8 ノードバッジ x.y 基準・DD-8 時点）／FND-79 "0.1"（doc-system/04-verification/02-findings.md の FND-79 ノードバッジ v0.1 時点）

### 内容

issue #30「必須辺の仕様化漏れ点検」として、コミット済み baseline の `docs/doc-system/config.yaml` の必須接続定義（`must_link_to` 31 行＋`must_be_linked_from` 13 行＝計 **44 行**・いずれも機械判定は RULE-006）が SPEC に網羅されているかを点検した。

**結論：完全な起票漏れはない。** 44 行すべての挙動は SPEC-8 の一般則（「RULE-006 をその config 行の severity（error/warning）で報告する」）が parametric にカバーする。正常系の通過は SPEC-5（構造違反 0 通過）・SPEC-17（検証層）・SPEC-29-1（分析層）が担う。

ただし **dedicated（行固有・テスタブル）SPEC を持つのは 44 行中 8 行のみ** で、被覆が大きく非対称になっている。

| config 行 | 種別 | dedicated SPEC |
|---|---|---|
| O→P | must_link_to | SPEC-30-1 |
| I←[P] | must_be_linked_from | SPEC-30-3 |
| E←[P] | must_be_linked_from | SPEC-30-2 |
| SPEC←[TD] | must_be_linked_from | SPEC-15-1 |
| TC→TD | must_link_to | SPEC-18-4 |
| TC←[TR] | must_be_linked_from | SPEC-18-2 |
| NFR←[FND,TC,VERIFY] | must_be_linked_from | SPEC-18-3 |
| VERIFY→any | must_link_to | SPEC-18-5 |

※ FND→any（SPEC-18-1）は main の Q-4→DD-16 で `fnd_lifecycle.unresolved.must_link_to` へ移動したため標準 44 行の対象外。fnd_lifecycle 系の dedicated 化は FND-103 で追跡（本 PR スコープ外）。

残り **36 行** は SPEC-8 一般則のみに依存し dedicated SPEC を持たない（要件骨格 8 行・分析層 12 行・設計層 12 行・実装/検証 4 行）。

### 論点

1. **昇格基準が未文書化**: どの行を dedicated（テスタブル）SPEC へ昇格するかの基準が文書化されておらず、現状は価値経路 3 種（O→P・I←[P]・E←[P]）＋検証層のみが ad-hoc に dedicated 化されている。
2. **トレーサビリティ表が不在**: config 行 → 被覆 SPEC の対応表が存在しないため、「必須辺の仕様化漏れ」を機械的に確認できない（＝issue #30 が懸念した状態そのもの）。
3. **FND-79 と同根**: 「同一 RULE が複数 SPEC に分散しているため索引化が必要」という FND-79（open・INFO）の指摘を、必須辺被覆の観点から具体化・補強する位置づけ。

（補足：SPEC-30 本文は「D の接続漏れは一般則 SPEC-8 でカバー、SPEC-30 は価値経路の名前付き 3 種のみ列挙」と明記。SPEC-48 は NFR-5「USDM 1 段制約＝祖先辺の禁止」であり、必須辺の欠如〔RULE-006〕とは別軸のため本点検の対象外。`fnd_lifecycle`（resolved.must_be_linked_from／must_not_link_to）の dedicated SPEC 化は FND-103 として別途追跡（本 PR は標準 44 行に限定）。）

### 推奨（オーナー提示用・3 案）

- **① 現状維持＋FND-79 索引化のみ（最小工数）**: SPEC-8 一般則で挙動規定済みとみなし、config 行→SPEC 対応を索引（connection-matrix 拡張等）で可視化するに留める。
- **② 全 44 行を dedicated・テスタブル SPEC 化（網羅最大・重い）**: 1 アサーション 1 SPEC を厳格適用。網羅は最大化するが SPEC が +36 で重く、SPEC-8 と内容が重複する。
- **③ トレーサビリティ表＋昇格基準の明文化（中庸・推奨）**: config 各行→covering SPEC 対応表を追加し、「どの行を dedicated 化するか」の基準（例：価値経路に面する辺・severity=error・新規型導入時）を明文化する。漏れの機械確認を可能にしつつ SPEC 爆発を回避できる。FND-79 の索引化要望とも両立する。

> 推奨は ③ だが、実施スプリント（今スプリント実施 vs 次スプリント繰り越し）の判断はオーナーに委ねる。独断で `scheduled` を設定しない（スケジュール独断禁止）。

### config.yaml 規則変更チェック（FND-99 パターン）

本 FND は **既存の必須辺定義の被覆状況を点検した指摘であり、`must_link_to`/`must_be_linked_from` などの接続規則の追加・変更・削除を含まない**。よって out-of-graph 著作資産（接続マトリクス・ドキュメント一覧・各 author エージェント／スキル）への規則伝播チェックは不要。推奨 ③ を採択して索引・対応表を整備する場合は、その整備時に connection-matrix／document-items 等への反映を別途検討する（本 FND 起票時点では伝播対象なし）。
