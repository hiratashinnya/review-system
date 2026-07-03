**改訂理由（z バンプ v0.1→v0.1.1・FND-110/DD-21 適用是正）**:
Q-4 選択肢A 採用（DD-16）により `fnd_lifecycle` 専用ルールが正式定義されたため、暫定措置の `suppress: [RULE-006]` を撤去し `resolved: true` で機械判定可能にする。本 FND は処置対象 MOD-1・DM-3・DM-5・DM-6 から `→FND-100`（backward 辺）を受けており、新 `fnd_lifecycle` の resolved ルール（backward 必須・forward 不在期待・`edges: []`）を満たす。指摘内容・深刻度・対応状況（resolved）は不変（suppress 撤去＋`resolved` フィールド追加＝lifecycle 操作のため MINOR バンプとして記録していたが、DD-21 の確定原則「resolved-FND の辺逆転/backref 付与は z バンプ」に照らし FND-110 で是正、z バンプへ訂正）。

**深刻度**: WARNING

**対応状況**: resolved（オーナーが本セッションで即時実施を承認済み＝独断繰り越しではない。`scheduled` は空のまま）

### 内容

FND-96（DM→MOD→D 正規化・選択肢A・sprint-1）の処置後、**MOD-1↔DM の被覆が非対称**であり、接続チェーン `DM → MOD → D` が一部経路で途切れている（PR6 連続性の部分残存）。

- **MOD-1（domain）が realize 宣言する D**（v0.2 時点の edges）: D-4・D-6・**D-9〜D-21**。
- **新設済み DM（DM-1〜4）が realize する D**: D-4（DM-1/DM-2）・D-6（DM-3）・**D-9〜D-16（DM-4）** のみ。
- → **D-17〜D-21（各検査ビュー型）に対応する DM 型ノードが存在しない**。これらは D-4 の単なる部分集合ではなく、D-4 に無い計算フィールド（in_degree / out_degree 等）を持つ**別の値オブジェクト型**であり、domain.py 上に独立した型が要る。DM 不在のため `DM → MOD → D` チェーンが D-17〜D-21 経路で途切れている。

加えて同じ非対称が次の 2 点に現れる:

1. **D-5（パース段違反リスト）**: D-6（RULE 違反リスト）と完全に同形（`list[ViolationRecord]`）であるにもかかわらず、MOD-1 は D-6 のみ realize し D-5 を realize していなかった（MOD-1↔D の非対称）。型は同一の「もの」（違反レコード 1 件）であり、発生源差（パース段 P-1 / RULE 検査段 P-2）は生成元プロセスの差として D ノード側で既に表現済み。
2. **D-7（カバレッジ計測結果）**: CoverageReport 型が MOD-1・DM のどちらにも不在で、`DM→MOD→D` チェーンが D-7 経路で完全に欠落していた。

**対象外**: D-22（グラフトポロジビュー）は `labels:[post-mvp]` のため本指摘の対象外。

**主たる指摘対象**: MOD-1（domain.py）。被覆漏れの所在は MOD-1 の realize 辺集合と新設 DM 群の被覆の差にある。

### 指摘時 ref_version

FND 解消時に辺が逆向きに張り直され（対象→FND）元の辺（FND→対象）が削除されるため、辺情報から指摘時の版が失われる。本文に明記する（DD-3 制度化）。

**指摘時 ref_version**: MOD-1 "0.2"（01-modules.md・MOD-1 バッジ v0.2 時点。realize 辺が D-4/D-6/D-9〜D-21 で D-5/D-7 を欠く状態＝辺逆転で削除した元 forward 辺の処置対象）／DM-3 "0.1"・DM-4 "0.1"（04-domain-model.md）／D-5・D-7・D-17〜D-21 "0.1"（02-io.md・被覆漏れの相手側の版＝provenance）

### 深刻度判定の根拠

機械 RULE 上、MOD-1 は `MOD → [P | D]`（OR・RULE-006）を D 辺で充足済みであり、新設 DM 群も `DM → MOD`・`DM → TERM` を充足している。被覆が非対称でも個々のノードは必須辺を満たすため、検証ツール上の live な RULE 失敗は発生しない。本件は「各ノードのルールは満たされているが、`DM → MOD → D` チェーンの被覆が一部経路で途切れる」**設計層の構造的な被覆漏れ（PR6 連続性の部分残存）**であり、FND-96（live RULE 失敗なし・WARNING）の判定基準に倣い **WARNING** と判定する。

### 対応内容（design-author 著作の DM/TERM/MOD 補完を反映）

被覆の非対称を是正するため、以下を著作・反映した:

1. **DM-3（ViolationRecord 型）v0.1→v0.2**: 「実現する D」に **D-5（パース段違反リスト）を追加**（D-6 と同形・新規型なし）。`→MOD-1` ref_version を MOD-1 更新後バッジ "0.3" に追従。`→FND-100` 付与。
2. **TERM-5・DM-5（CoverageReport）新設**: D-7 の FR×condition カバレッジテーブル部を表す novel 型。D-7 の網羅性穴リスト部は引き続き DM-3（ViolationRecord）が担う協働。MOD-17 が `measure_spec_coverage(...) -> CoverageReport` で型名を命名済み。DM-5 に `→FND-100` 付与。
3. **TERM-6・DM-6（InspectionViews 型群）新設**: **D-17〜D-21 を 1 ノードで一括 realize**。先例 DM-4（ConfigSlice 型群）と射影系として構造一致。MOD-13 が `project_views(node_set) -> InspectionViews` で集約戻り値型を命名済み。DM-6 に `→FND-100` 付与。
4. **MOD-1 v0.2→v0.3**: realize 辺に **D-5・D-7 を追加**（各 D 現バッジ "0.1"）。D-17〜D-21 は既存辺あり。`→FND-100` バックリファレンス付与（FND-100 の forward 辺を逆転した辺）。

これにより設計層の被覆が対称化し、`DM → MOD → D` チェーンが D-5（DM-3）・D-7（DM-5＋DM-3）・D-17〜D-21（DM-6）の全経路で連続する（PR6 充足）。

> **バックリファレンスの扱い**: 処置対象 MOD-1・DM-3・DM-5・DM-6 はいずれも実在ノード（付与先あり）のため、各ノードに `→FND-100`（ref_version "0.1"）を付与済み。削除済みの処置対象はなく「付与先なし」項目は該当なし。D-5/D-7/D-17〜D-21（D ノード側）には本対応で `→FND-100` を張らない（被覆の主体は MOD-1 realize 辺と DM 群であり、FND-96 でも D ノード側には張らず MOD-1 が張り返した先例に倣う）。

> **config.yaml 規則変更なし**: 本対応は既存規則（`DM→TERM`・`DM→MOD`・`MOD→[P|D]`・`TERM→SPEC`）に準拠するノード著作のみで config.yaml の `must_link_to`/`must_be_linked_from` を変更しない。よって out-of-graph 著作資産への規則伝播チェック（FND-99 パターン）は不要。

> **🟡 注記（決定済みトレードオフ・新規是正対象でない）**: PR #32 は `MOD → [P | D]` の OR 化により「ドメイン型モジュール → D／処理モジュール → P」の型別強制が機械判定で効かなくなる点（処理モジュールが誤って D のみを張っても RULE-006 上は合格）を 🟡 として挙げている。これは FND-96 選択肢A（オーナー承認済み・config.yaml L44）で織り込み済みのトレードオフであり、本 FND-100 の新規是正対象ではない。設計レビュー（人/LLM）・asset-auditor・spec-inspector の点検でカバーする運用前提。独立追跡のための別ノード化（INFO FND/DD・subject `→FND-96`・config.yaml L44 所在）はオーナー判断に委ねる（独断で起票も「対応不要」も結論づけない）。
