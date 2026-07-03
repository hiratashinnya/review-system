**深刻度**: WARNING

**改訂理由（z バンプ v0.4→v0.4.1・FND-110/DD-21 適用是正）**:
Q-4 選択肢A 採用（DD-16）により `fnd_lifecycle` 専用ルールが正式定義されたため、暫定措置の `suppress: [RULE-006]` を撤去し `resolved: true` で機械判定可能にする。本 FND は既に元 forward 辺を削除し（`edges: []`）処置対象 MOD-1（v0.2）から `→FND-96`（backward 辺）を受けており、新 `fnd_lifecycle` の resolved ルール（backward 必須・forward 不在期待）を満たす。指摘内容・深刻度・対応状況（resolved）は不変（suppress 撤去＋`resolved` フィールド追加＝lifecycle 操作のため MINOR バンプとして記録していたが、DD-21 の確定原則「resolved-FND の辺逆転/backref 付与は z バンプ」に照らし FND-110 で是正、z バンプへ訂正）。

**改訂理由（MINOR バンプ v0.3→v0.4）**:
選択肢A（DM→MOD→D 正規化・フル実施）を sprint-1 で適用・完了し、対応状況を resolved に更新。実施した処置は以下のとおり。(1) `config.yaml` の `MOD → P`（必須・単一ターゲット）を `MOD → [P | D]`（OR）へ変更し、`DM → P` を `DM → MOD` へ変更（`DM → TERM` は維持）。(2) MOD-1 の `→P-1` 辺を削除し、realize するデータ型概念 D-4・D-6・D-9〜D-21 への辺へ変更（MOD-1 を MINOR バンプ v0.1→v0.2・`→FND-96` バックリファレンス付与）。(3) TERM-1〜4（NodeRecord / EdgeRecord / ViolationRecord / ConfigSlice）を新設。(4) DM-1〜4（各型の DM ノード・`→TERM` + `→MOD-1`）を新設。指摘対象・深刻度は変更しない（処置完了の記録のため MINOR バンプ）。MOD-1 が `→FND-96` を張り返すため FND-96 自体の forward 辺（`→MOD-1`）は削除し、`suppress: [RULE-006]` を付与（resolved FND の辺逆転ルール）。指摘時 ref_version は本文に記録済み（DD-3）。

**改訂理由（MINOR バンプ v0.2→v0.3）**:
オーナーが選択肢A（DM→MOD→D 正規化・フル実施）・実施スプリント sprint-1 を決定。
対応状況を「選択肢A 確定（sprint-1 実施予定）」に更新。
設計修正（config.yaml・MOD-1 辺変更・DM/TERM ノード著作）は別コミットにて実施。

**改訂理由（MINOR バンプ v0.1→v0.2）**:
v0.1 は「MOD-1 が `MOD→P` を張っているのは category error」という**局所的な指摘**に留まっていた。オーナーとの議論で、本質は設計層の**接続チェーン構造ごと誤っている**点（正しくは `DM → MOD → D`）にあると確認された。これに伴い、(1) タイトルを接続チェーン欠落の問題として書き直し、(2) 正しいチェーン `DM→MOD→D` の説明・PORT→MOD パターンとの対比を追加、(3) 現状 config.yaml の誤り（`DM→P`／`MOD→P` 単一ターゲット）を2点明記、(4) 選択肢 A/B/C を DM→MOD→D 正規化を軸に改訂した。指摘対象・edges・深刻度・対応状況は変更しない（内容拡充のため MINOR バンプ）。

**内容**:
`config.yaml` の必須辺 `{ node: MOD, target: P, activate_stage: design, severity: error, reason: "MODはプロセスを実装" }`（L44）は **「全モジュールはプロセスを実装する」と暗黙に仮定**している。しかし設計層には**プロセスを実装しないモジュール**（データ型を定義するモジュール）が存在し、本来あるべき接続チェーン **`DM → MOD → D`** が欠落している。

**正しいチェーン（オーナー確認済み）**:

```
DM（型定義: NodeRecord 等）
  → MOD（モジュールファイル: domain.py）
      → D（ランタイムのデータ概念: D-4 構造化ノードセット 等）
```

- `DM → MOD`：型定義はモジュールに属す。これは既存の **`PORT → MOD`**（ポート Protocol 定義はモジュールに属す）と同じ接続パターンであり、設計層は既にこの「定義要素 → モジュール」の向きを採用している。
- `MOD → D`：データ型モジュールは D（ランタイムのデータ概念）を実現する。
- 処理（ユースケース）モジュールは `MOD → P` で正しい（MOD-2〜9・13〜18 は現状維持）。

**現状 config.yaml の誤り（2点）**:
1. `DM → P`（必須）：DM は直接 P を指すのでなく **MOD を介すべき**。`DM → MOD` に変更が必要（`DM → TERM` は維持）。
2. `MOD → P`（必須・単一ターゲット）：データ型モジュールは P でなく **D を実現**するため、単一ターゲット強制が誤り。`MOD → [P | D]`（OR）が正しい。

この2点の強制により、データ型モジュール（MOD-1）は本来 realize すべき**データ D を指せず**、発生源（プロセス P）の辺で代用せざるを得ない。これは **PR1「もの＋発生源で分ける」違反**——データ（もの）をプロセス（発生源）の辺で表現する category error である。

- **MOD-1（domain）**：責務は「NodeRecord / EdgeRecord / ViolationRecord / ConfigSlice 等の値オブジェクトを定義する」＝**データ型の定義のみ**。プロセスを実装しない。にもかかわらず `MOD-1 → P-1`（ノード受付・パース）の辺を便宜的に張っており、本来は `MOD-1 → D`（自分が realize するデータ）であるべきところを、`MOD→P` 単一強制のために P の辺で表している。

MOD-1 が定義するデータ型と分析層 D の対応:
- NodeRecord / EdgeRecord ↔ **D-4（構造化ノードセット）**
- ViolationRecord ↔ **D-6（RULE 違反リスト）**
- ConfigSlice ↔ **D-9〜D-16（config 各スライス）**
- 消費スライス値オブジェクト ↔ **D-17〜D-21（検査ビュー）**

追跡性は損なわれない：分析層に既に `D → P`（内部データは生成プロセスに依存・config L37）があるため、`DM → MOD-1 → D → P` で型→設計→分析→プロセスの追跡経路が連続する（PR6 を満たす）。

**主たる指摘対象**: MOD-1（domain.py）

**同種の影響ノード（併記）**:
- **MOD-10（ports.py）**：FileSystemPort Protocol を定義（PORT-1 を実現・被参照あり）。プロセスでない。現状 `→P-1` は便宜的。PORT 型定義の辺設計は別途精査（選択肢A 参照）。
- **MOD-11（adapters/fs.py）**：FileSystemPort を実装するアダプタ。プロセスでない。現状 `→P-1`。アダプタは独立概念として別途精査。
- **MOD-12（__main__.py）**：合成ルート＋CLI。ORC-1/E-1 を実現すべき結線役。現状 `→P-5` は恣意的。合成ルートは独立概念として別途精査。
- ユースケース系（MOD-2〜9・MOD-13〜18）の `→P` は責務とプロセスが一致しており**正しい**＝本指摘の対象外。

**指摘時 ref_version**: MOD-1 "0.1"（01-modules.md v 時点）／MOD-10 "0.1"／MOD-11 "0.1"／MOD-12 "0.1"（いずれも 01-modules.md v 時点）

**深刻度判定の根拠**:
機械 RULE（MOD→P＝RULE-006）は MOD-1/10/11/12 とも `→P` 辺を保持しており**現状は充足**しているため、検証ツール上の live な ERROR 違反は発生していない。一方で、これは「ルールが満たされているのに辺の意味と接続チェーン構造が原則と食い違う」**設計層の構造的な原則違反（PR1 category error・DM→MOD→D チェーンの欠落）**であり、放置すると設計→分析の追跡が誤った相手（P）を指し続ける。既存の構造的・原則違反 FND の判定（live RULE 失敗を伴わない原則違反は WARNING）に倣い **WARNING** と判定する。

**選択肢（オーナー判断）**:

- **選択肢A（採用・DM→MOD→D 正規化・フル実施）**：
  - `config.yaml`：`MOD → [P | D]`（OR）へ変更、`DM → P` を `DM → MOD` へ変更（`DM → TERM` は維持）。
  - MOD-1 の edge を D-4・D-6・D-9〜16・D-17〜21 へ変更。
  - DM ノードを新設（NodeRecord・EdgeRecord・ViolationRecord・ConfigSlice 等 → MOD-1 + 対応 TERM）。
  - TERM ノードを新設（各型に対応する用語定義）。
  - MOD-10・11・12 の辺設計も別途精査（PORT 型定義・アダプタ・合成ルートはそれぞれ別概念）。
  - 根拠：PR1・追跡性が最も完全。設計層の全レイヤー（DM→MOD→D）が揃う。
  - コスト：TERM + DM ノードの新規著作が必要（分量あり）。

- **選択肢B（中間・ルール修正＋MOD-1 辺変更のみ）**：
  - `config.yaml`：`MOD → [P | D]`（OR）へ変更、`DM → P` を `DM → MOD` へ変更。
  - MOD-1 の edge を D へ変更。
  - DM・TERM ノードの新設は後続スプリントへ繰り越し。
  - 根拠：ルールの意味的誤りを今すぐ解消し、DM/TERM の著作は後続で行う。最小変更で config 整合を先行できる。
  - コスト：DM/TERM ノードが存在しない間は `DM→MOD` ルールが事実上発火しない（発火開始ステージが design であるため DM ノード著作まで RULE は待機状態）。

- **選択肢C（現状維持）**：
  - 据え置き。原則違反（DM→MOD→D チェーンの欠落・PR1 category error）が残る。

**推奨**: **A**。B は中間として成立するが、`DM→MOD` ルールに対応するノード（DM）が存在しない状態が続く。A の TERM + DM ノード著作は作業量があるが、設計層の完全性（PR6・DM→MOD→D の連続）のために必要。C は違反据え置きとなる。実施スプリントはオーナー判断（`scheduled` は空のまま）。

**対応状況**: resolved

**対応内容**（選択肢A 適用・sprint-1 完了）:
- **config.yaml**（`docs/doc-system/config.yaml`）：必須辺 `{ node: MOD, target: P, ... }` を `{ node: MOD, target: [P, D], ... }`（OR・reason: "MODはプロセスを実装（処理系）またはデータ型を実現（D）"）へ変更。`{ node: DM, target: P, ... }` を `{ node: DM, target: MOD, ... }`（reason: "DM型定義はモジュールに属す（DM→MOD→D チェーン）"）へ変更。`DM → TERM` は維持。
- **MOD-1**（`doc-system/05-design/01-modules.md`）：`→P-1` 辺を削除し、realize するデータ型概念へ辺を変更（D-4 "0.2"・D-6 "0.1"・D-9 "0.2"・D-10〜13 "0.1"・D-14 "0.2"・D-15〜21 "0.1"）。`→FND-96`（ref_version "0.3"）バックリファレンス辺を付与。MINOR バンプ v0.1→v0.2。
- **TERM-1〜4 新設**（`doc-system/03-analysis/05-terms.md`）：TERM-1 NodeRecord・TERM-2 EdgeRecord・TERM-3 ViolationRecord・TERM-4 ConfigSlice の用語定義を著作。
- **DM-1〜4 新設**（`doc-system/05-design/04-domain-model.md`）：DM-1 NodeRecord型・DM-2 EdgeRecord型・DM-3 ViolationRecord型・DM-4 ConfigSlice型群を著作（各 `→TERM` + `→MOD-1`）。
- これにより設計層の接続チェーン `DM → MOD → D` が確立し、MOD-1 はデータ（もの）を D の辺で表現するようになった（PR1 category error 解消）。追跡経路 `DM → MOD-1 → D → P` が連続し PR6 を満たす。
- バックリファレンス辺は処置対象 MOD-1（v0.2）側に reconciliation 反映時に付与済み。FND-96 自体の edges は MOD-1 が張り返すため現状維持（`→MOD-1` のみ）。
