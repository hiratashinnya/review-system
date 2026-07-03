**深刻度**: WARNING

**改訂理由（z バンプ v0.1.1→v0.1.2・内容のみ訂正）**:
本 PR（同一コミット）で新設された **Q-5 が `→FND-101`（ref_version "0.1"）の義務辺**を持つため、FND-101 は incoming 辺を1本持ち、**完全孤立しておらず RULE-005（完全孤立・always_error）は発火しない**。従来本文（v0.1.1）の「`→Q-4` 削除後は incoming/outgoing をともに持たず完全孤立し、RULE-005 を意図的に発火・保持する」とする記述は、Q-5 新設前の状態を前提とした事実誤りであったため、Q-5→FND-101 の被参照により非孤立となった実態へ訂正する（孤立前提の「意図的シグナル」論は撤回）。機械検証で `FND-101` の out_edges=[]、in=['Q-5'] を確認済み。本文のみの変更のため z バンプ（DD-8 §4 準拠）。

> **被参照の確保（Q-5 昇格辺により非孤立・RULE-005 非発火）**: 本 FND の処置対象は「辺逆転を一括是正した全 resolved FND（FND-1〜95 ほか）」というバッチであり、単一の in-graph 処置対象ノードを持たない（90 件超への backref 列挙は非現実的かつ各 resolved FND の処置対象は各自の対象ノードである）。よって `対象 → FND-101` のバックリファレンスを処置対象側に張る先は存在しない。しかし本 FND は孤立しているわけではない——本論点（resolved-FND 辺逆転の版バンプ・backref/provenance 辺の drift 扱い）を扱う質問ノード **Q-5 が本 FND-101 を親論点として `→FND-101`（ref_version "0.1"）で参照**しており、FND-101 は incoming 辺を1本持つ。これは正当な被参照であり（むしろ FND-101 が Q-5 から辿れる健全な状態）、`RULE-005（完全孤立・always_error）は発火しない`。`suppress` は不要（孤立エラー自体が発生しないため抑制対象がない）。本是正の根拠は DD-16（fnd_lifecycle 正式化）であり、provenance として本文に記録する。

**対応状況**: resolved（sprint-1 で FND-1〜95 ほかの辺逆転を一括是正・オーナー即時実施承認 2026-06-24）

**指摘時 ref_version**: Q-4 "0.1"（05-questions.md の Q-4 バッジ v0.1 時点・本 FND の是正方針が依存した未決論点＝provenance。Q-4 は DD-16 へ昇格 closed 済み）／是正根拠＝DD-16（fnd_lifecycle 正式化・04-decisions.md・provenance）

### 内容

resolved 済み FND の大部分（**FND-1〜FND-95** の範囲）が、解消後も元の forward 辺（FND → 処置対象）を削除しておらず、FND の辺逆転ルール（DD-3／verification-author 規約）に違反している。

**辺逆転ルール（正しい resolved FND の形）**:
- 処置対象ノード側に `対象 → FND-x` の被参照辺（バックリファレンス）を張る。
- FND 側の元の forward 辺（FND → 対象）は**削除**する。
- 指摘時 ref_version は辺から失われるため、FND 本文に明記して移動する（DD-3）。

**現状（起票時に Read で確認した違反パターン）**:
FND-1〜95 の resolved FND では、処置対象側へのバックリファレンス付与（`対象 → FND-x`）は概ね行われている一方で、**FND 側の元 forward 辺（FND → 対象）が削除されずに残置されている**。すなわち「対象 → FND」と「FND → 対象」の**双方向辺が併存**し、辺逆転（forward を消して backward へ張り替える）が完了していない。汎用ルール `{ node: FND, target: any }`（config.yaml L60・通称 RULE-006・forward 必須）が forward 辺の残置を許す（むしろ要求する）ため、live な RULE-006 エラーは発生せず、違反が機械検知されないまま蓄積している。

### 深刻度判定の根拠

**WARNING**。残置された forward 辺はむしろ汎用 RULE-006（FND→any・forward 必須）を充足するため live な機械 RULE 失敗は発生しないが、resolved FND の本来の意味（処置対象から指される＝過去の指摘の証跡）に反し、トレース・被覆解析で double-edge が誤読・ノイズを生む構造的負債である。既存の構造的・原則違反 FND（live RULE 失敗を伴わない構造的ドリフトは WARNING）に倣う。

### 是正方針（Q-4→DD-16 決定で確定）

Q-4 選択肢A が採択され DD-16 として `fnd_lifecycle` 専用ルール（unresolved: forward 必須／resolved: backward 必須＋forward 不在期待）が正式定義されたため、これに合わせて FND-1〜95 ほかの元 forward 辺を一括削除し、`resolved: true`・`edges: []` を付与、指摘時 ref_version を各 FND 本文へ移動する是正を sprint-1 で実施した（FND-96/97/98/100 で用いた暫定 `suppress: [RULE-006]` は DD-16 で不要となり撤去）。

### 対応内容（sprint-1 一括是正）

- 全 resolved FND（FND-1〜95 ほか）について、元 forward 辺を削除し `edges: []`・`resolved: true` を付与（z バンプ）。
- forward 辺の ref_version を各 FND 本文の「指摘時 ref_version」に移動（DD-3）。
- provenance 辺（FND→DD / FND→他 FND / FND→Q）は削除し本文記録のみとし、backref は張らない。
- 実処置対象が in-graph に存在する FND は対象ノード側に `対象 → FND-x` backward 辺を付与（reconciliation が他層ファイルへ反映）。実処置対象が out-of-graph（PR description・dashboard・.gitignore 等）で backref 対象が存在しない FND（FND-37/38/99 等）は、孤立エラーを意図的に保持（FND-99 先例・suppress なし）。
- 本 FND-101 自身も上記方針で resolved 化したが、本論点を扱う Q-5 が `→FND-101` の義務辺を持つため非孤立であり、孤立保持の対象には含まれない（v0.1.2 で訂正）。
