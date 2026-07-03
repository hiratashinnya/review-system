**深刻度**: INFO

**改訂理由（z バンプ v0.2.0→v0.2.1・DD-16 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠。当初 MINOR は誤りで Q-5/DD-21 により訂正）**:
DD-16（fnd_lifecycle 正式化）に伴い FND-101 辺逆転コホートの一括是正として辺逆転を完了。元 forward 辺 `→SPEC-18-1`（ref_version "0.1"）・`→FND-102`（ref_version "0.2"）を削除し `edges: []`・`resolved: true` を付与した（従来 baseline 慣行で保持していた forward 辺を本是正で削除）。処置対象の新 SPEC（SPEC-18-9・SPEC-59）から `→FND-103` の backward 辺を受けており、resolved ルール（backward 必須・forward 不在期待）を満たす。`→FND-102`（他 FND・同根コホート）は provenance であり辺を削除し関連は本文に記録（DD-16 と同型：→FND は付与せず provenance を本文に記す・FND-102 側に backref は付与しない）。指摘時 ref_version は本文に記録済み（DD-3）。

> **SPEC-18-1 backref の重複回避（worklist 確認事項）**: 本 FND は元 forward 辺 `→SPEC-18-1` を持っていたが、resolved 後の `must_be_linked_from`（backward 必須）は**処置成果である SPEC-18-9・SPEC-59 から既に受けている**（spec.md に `→FND-103` 既存）。よって SPEC-18-1 → FND-103 の backref 追加は不要（重複回避）。worklist §36 の「SPEC-18-1 → FND-103」は本注記により追加不要と確定する。

**根拠（深刻度確定の理由）**: 現状 SPEC-8 の parametric 一般則（「RULE-006／必須辺欠如をその config 行の severity で報告」）と config の `fnd_lifecycle` 定義そのものが3ルールすべての挙動を規定済みで、機械判定上の挙動は定義済み・実害ゼロ。残る課題は「fnd_lifecycle 系の3ルールのうち resolved 系2ルールが dedicated（行固有・テスタブル）SPEC を欠き、被覆が不均一」というドキュメント／テスト被覆均一化の論点に留まる。FND-102（issue #30 本体）が標準必須辺44行を全て dedicated 化した結果、相対的に fnd_lifecycle 系の dedicated 欠如が目立つ位置づけになったが、これは現状の欠陥ではなく被覆均一化の整備論点であるため、同根の FND-79（RULE 分散→索引化・open・INFO）・FND-102（INFO）と決定の一貫性を保ち **INFO** とする。

**対応状況**: resolved（2026-06-22・②案完了／2026-06-25・DD-16 辺逆転完了）。オーナー決定により案②（resolved 系2ルールを dedicated SPEC 化）を採用し、resolved 系2ルールを全 dedicated 化して被覆を均一化した:

- `resolved.must_be_linked_from`（any→FND・error）→ **SPEC-18-9** で dedicated 被覆（03-spec.md 反映済み）。
- `resolved.must_not_link_to`（FND→any 不在期待・warning）→ **SPEC-59** で dedicated 被覆。SPEC-59 は本処置で新設した **RULE-030**（config 駆動の禁止接続/辺残留・FND-104／DD-17 で新設）を引く。

これで fnd_lifecycle 系3ルール（unresolved.must_link_to＝SPEC-18-1／resolved.must_be_linked_from＝SPEC-18-9／resolved.must_not_link_to＝SPEC-59）がすべて config 行→dedicated SPEC の 1:1 台帳に組み込まれ、issue #30 の被覆均一化が fnd_lifecycle 系にも拡張された。処置対象の新 SPEC（SPEC-18-9・SPEC-59）から `→FND-103` のバックリファレンス辺を受ける。なお元 forward 辺（→SPEC-18-1・→FND-102）は、当初 FND-101 辺逆転コホートの一括是正対象として保持していたが、本是正（2026-06-25）で削除し `edges: []`・`resolved: true` を付与して辺逆転を完了した。

### 内容

main の Q-4→DD-16（commit 52093ed）で `config.yaml` に正式化された FND ライフサイクルルール `fnd_lifecycle` は、必須辺ルールを3つ定義する:

| fnd_lifecycle ルール | 辺の向き | severity | dedicated SPEC |
|---|---|---|---|
| `unresolved.must_link_to`（FND→any） | forward 必須 | error | **SPEC-18-1（被覆済み）** |
| `resolved.must_be_linked_from`（any→FND） | backward 必須 | error | **SPEC-18-9（②案で新設）** |
| `resolved.must_not_link_to`（FND→any 不在期待） | forward 不在期待 | warning | **SPEC-59（②案で新設・RULE-030 経由）** |

`unresolved.must_link_to`（FND→any）は SPEC-18-1「FND に被指摘要素への辺欠如（RULE-006）」が dedicated 被覆していた。残る `resolved.must_be_linked_from`（any・error＝resolved FND は処置対象からの backward 辺必須）と `resolved.must_not_link_to`（any・warning＝resolved FND の元 forward 辺は削除済みであること）には dedicated（行固有・テスタブル）SPEC が存在しなかったが、②案採用により SPEC-18-9・SPEC-59 を新設して被覆を均一化した。

issue #30 が目指した「config 行→被覆 SPEC の 1:1 トレーサビリティ台帳」が fnd_lifecycle 系にも拡張され、本残課題は解消した。

### 位置づけ（スコープ境界）

- issue #30（FND-102）は **標準必須辺44行**（`must_link_to` 31＋`must_be_linked_from` 13）に限定して全行 dedicated 化したため、`fnd_lifecycle` 系3ルールは FND-102 の対象外（オーナー決定）。本 FND-103 がその残課題を別途追跡し、②案で解消した。
- FND-101／Q-4 の **辺逆転コホート**（resolved FND の forward 削除・backward 付与）と同一系統。resolved 系2ルール（must_be_linked_from／must_not_link_to）はまさに辺逆転後の resolved FND の構造を機械判定するルールである。本 FND 自身も本是正で辺逆転を完了し、自らが規定する resolved 構造に適合した。
- FND-79（RULE-006/025/026 が複数 SPEC に分散→索引化・open・INFO）とも同根で、「同一 RULE 系の被覆均一化・索引化」という横断課題の一部。

### 推奨（オーナー提示用・2 案）

- **① 現状維持**: SPEC-8 の parametric 一般則＋config の `fnd_lifecycle` 定義自体で挙動は規定済みであり、行固有 SPEC を起こさない。fnd_lifecycle 系の可視化は索引化論点（FND-79 の領分）に委ねる。
- **② resolved 系2ルールに dedicated SPEC を新設**: `resolved.must_be_linked_from`（any・error）と `resolved.must_not_link_to`（any・warning）に行固有・テスタブルな SPEC（SPEC-18 傘の拡張等）を新設し、fnd_lifecycle 系も config 行→SPEC の 1:1 台帳に組み込む。被覆は均一化するが SPEC が +2 増え、SPEC-8 一般則と内容が一部重複する。

> 推奨は実施時期を含めオーナー判断に委ねる。現状実害ゼロ（INFO）のため独断で `scheduled` を設定しない（スケジュール独断禁止・CLAUDE.md）。AI が独断で「対応不要」「将来検討でよい」と結論づけない（PR7・独断禁止）。
>
> **決定: 案②（resolved 系2ルールを dedicated SPEC 化）採用**（オーナー決定・2026-06-22）。SPEC-18-9（must_be_linked_from）・SPEC-59（must_not_link_to・RULE-030 経由）を新設して被覆を均一化した。SPEC-59 が引く RULE-030 の新設は DD-17 / FND-104 で決定。

**指摘時 ref_version**: SPEC-18-1 "0.1"（doc-system/02-what/03-spec.md の SPEC-18-1 ノードバッジ v0.1 時点）／FND-102 "0.2"（doc-system/04-verification/02-findings.md の FND-102 ノードバッジ v0.2 時点・provenance＝同根コホート）。なお被指摘対象の `fnd_lifecycle` 定義は `docs/doc-system/config.yaml`（DD-16・Q-4 から昇格・main commit 52093ed）に存在するが、config.yaml はノード化されないため辺は張れず、本文で参照を明記する（SPEC-18-1＝fnd_lifecycle の被覆済みルールを forward 辺の代表対象としていた）。

### config.yaml 規則変更チェック（FND-99 パターン）

本 FND は **`fnd_lifecycle` の既存ルールの dedicated SPEC 被覆状況を指摘するもので、`must_link_to`/`must_be_linked_from`/`fnd_lifecycle` 等の接続規則の追加・変更・削除を含まない**（規則自体は main の Q-4→DD-16 で既にコミット済み・本 FND はその被覆論点を起票するのみ）。②案の処置（SPEC-18-9・SPEC-59 の dedicated SPEC 新設）も config 接続規則の変更ではなく、既存ルールに対する dedicated SPEC の追加に留まる（SPEC-59 が引く RULE-030 の台帳追加は DD-17 で別途記録・接続規則変更ではない）。よって out-of-graph 著作資産（接続マトリクス・ドキュメント一覧・各 author エージェント／スキル）への規則伝播チェックは不要。
