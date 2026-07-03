**status: closed**（2026-06-21 DD-16 へ昇格・選択肢A 採用確定）

**改訂（MINOR バンプ v0.1→v0.2・辺追加＝構造変更）**: オーナーが選択肢A（FND 専用ライフサイクルルールを config に独立定義）を承認したため、本 Q を DD-16 へ昇格し `status: closed` とする。義務辺 `→DD-16`（ref_version "0.1"・DD-16 現バッジ v0.1）を追加し、本 Q が DD-16 へ昇格したことを辺で明示する（Q→DD 昇格辺）。DD-16 が `fnd_lifecycle` 専用ルール（未解消＝forward 必須／resolved＝backward 必須・forward 不在期待）・FND の `resolved` フィールド導入・FND-96/97/98/100 の暫定 `suppress: [RULE-006]` 撤去を決定した。指摘時 ref_version（FND-96 "0.4"・DD-3 "0.1"）は据え置き（既存の指摘時 ref_version 記録を維持）。

**指摘時 ref_version**: FND-96 "0.4"（02-findings.md の FND-96 バッジ v0.4 時点・暫定 `suppress: [RULE-006]` を持つ resolved FND の代表例として指す）・DD-3 "0.1"（04-decisions.md の DD-3 バッジ v0.1 時点・FND の辺逆転＝指摘時 ref_version 本文記録を制度化した決定）

**論点（1文）**: FND の必須接続は現状、汎用ルール `{ node: FND, target: any }`（config.yaml L60・通称 RULE-006）で代用されているが、これは FND 固有のライフサイクル（**未解消＝対象を指す／解消＝対象から指される**という辺の向きの逆転）を汎用の依存辺ルールで無理に表現しており、resolved FND が forward 辺を残すか `suppress: [RULE-006]` で抑制するかの歪みを生む。FND 専用のライフサイクルルールを独立定義すべきか。

**現状の歪み（Read で確認）**:
- config.yaml の `must_link_to: { node: FND, target: any }`（L60・severity error）は **「FND は対象要素への forward 辺を1本以上持つ」** ことしか強制できない。これは未解消 FND には正しいが、resolved FND の本来形（処置対象→FND の被参照辺へ張り直し・元の forward 辺は削除・指摘時 ref_version は本文へ移動＝DD-3）と衝突する。
- 結果として resolved FND の表現が二分されている:
  - **forward 辺を残す系（FND-1〜95 の大部分）**: 処置対象側に `→FND-x` のバックリファレンスを付与しつつ、FND 側の元 forward 辺（FND→対象）を削除せず残している。RULE-006 は forward 辺で充足されるため live エラーは出ないが、辺逆転ルールに違反し、誤った forward 辺がグラフに残留する（→ FND-101 で別途起票）。
  - **forward 辺を削除し `suppress: [RULE-006]` を付す系（FND-96/97/98/100）**: 辺逆転ルールに従い元 forward 辺を削除した結果、汎用 RULE-006（forward 辺必須）に抵触するため、暫定措置として `suppress: [RULE-006]` を付与している。これは「ルールが FND ライフサイクルに合っていないために抑制で逃げている」状態であり、抑制の濫用に近い。
- FND-99 は処置対象が out-of-graph 資産のため forward 辺を削除した上で `suppress` を付けず、RULE-005（完全孤立・always_error）を意図的に発火させている（→ FND-99 改訂）。これも汎用ルールでは「resolved だがバックリファレンス対象が未著作」を正しく表現できないことの現れ。

**オーナー提示のルール案（選択肢の中核）**:
- **未 Resolved 時**: any タイプ**への**参照を必須とする（forward 辺・FND→対象）。
- **Resolved 時**: any タイプ**からの**参照を必須とする（backward 辺・対象→FND）。
- **Resolved 時**: 元の指摘対象への forward 辺は削除し、指摘時 ref_version 付きで本文へ移動する（DD-3 のもともとのルール）。

**選択肢（排他・トレードオフ）**:

- **選択肢A（FND 専用ライフサイクルルールを config に独立定義・状態依存の必須辺＝推奨）**:
  - 汎用 `{ node: FND, target: any }`（L60）を FND の対応状況に依存する専用ルールへ置き換える。機構として、FND の状態（未解消／resolved）を機械判定可能な属性（例: 本文バッジでなくメタ属性 or 専用フィールド）に格上げし、(1) 未解消 FND は `must_link_to: FND → any`（forward 必須）、(2) resolved FND は `must_be_linked_from: FND ← any`（backward 必須）かつ forward 辺の不在を期待、という状態別ルールを定義する。
  - トレードオフ＝機械判定が FND ライフサイクルを正しく表現でき、`suppress: [RULE-006]` の暫定措置が不要になる。一方で、FND の状態を機械可読化する仕組み（対応状況のメタ属性化 or 専用ルールの状態分岐）が必要で、config スキーマ・パーサ・接続規則の3点に変更が及ぶ。**機械判定（状態別必須辺）と運用ルール（処置時に forward を消し ref_version を本文へ移す手順）は分離して定義する（PR2）**——前者は config の機構、後者は verification-author/reconciliation の運用ルールに留める。

- **選択肢B（運用ルールのみで担保・config は汎用 RULE-006 のまま据え置き）**:
  - config は変更せず、resolved FND は `suppress: [RULE-006]` を付ける（または forward 辺を残す）運用ルールを正式化して文書化のみで担保する。
  - トレードオフ＝config 変更コストはゼロだが、`suppress` の濫用または forward 辺残留のどちらかが恒久化し、辺逆転ルールが機械判定で守られない（運用任せ）。**機械判定と運用ルールの混在（PR2 違反）が残る**ため非推奨。

- **選択肢C（現状維持・暫定措置を恒久化）**:
  - resolved FND の表現が forward 残し系と `suppress` 系で割れたまま放置する。
  - トレードオフ＝何も決めないため最小コストだが、FND-101（forward 辺残留）と本 Q の歪みが恒久化し、グラフのトレース整合性が損なわれ続ける。単一責務・機械判定明確化の方向に逆行するため非推奨。

**推奨**: **選択肢A（FND 専用ライフサイクルルールを config に独立定義）**。理由：(1) FND の「未解消＝指す／解消＝指される」という辺の逆転は FND 固有のライフサイクルであり、汎用の `target: any` 依存辺では表現しきれない構造的ミスマッチ（PR1 もの＋発生源で分ける／単一責務＝1ルール1責務）。(2) 専用ルール化により `suppress: [RULE-006]` の暫定措置が不要になり、抑制の濫用を排除できる（抑制は本来「ルールの例外」であって「ルールがライフサイクルに合っていない代用」ではない）。(3) 機構（状態別必須辺）と運用（処置手順）を PR2 に従い分離して定義できる。B は機械判定の穴を運用任せにし PR2 違反が残るため非推奨、C は歪みの恒久化で非推奨。**ただし採否・config スキーマへの状態メタ属性導入の要否・実施スプリントはオーナー判断**（独断でのスプリント繰越は禁止＝CLAUDE.md「スケジュール独断禁止」。本 Q は `scheduled` を空のままとし判断を仰ぐ）。決定後は DD へ昇格（id 通貫）。

**影響範囲（選択肢A 採用時）**:
- `config.yaml`: 汎用 `{ node: FND, target: any }`（L60・must_link_to）を FND 状態別の専用ルール（未解消＝forward 必須／resolved＝backward 必須・forward 不在期待）へ置換。FND の対応状況を機械可読化する仕組み（メタ属性 or ルールの状態分岐）の設計が必要。
- 検証ロジック（パーサ・ルールエンジン）: FND 状態の判定と状態別ルールの分岐を実装（設計層への波及）。
- **暫定措置の撤去（必須・トレース）**: 本ルールが正式化・実装された暁には、辺逆転ルールに整合させるための暫定措置として付与した **FND-96 / FND-97 / FND-98 / FND-100 の `suppress: [RULE-006]` を撤去する修正が必要**である。これらの `suppress` は「専用ルール不在ゆえの代用」であり、専用ルール導入後は不要になる（撤去しなければ抑制の死蔵となる）。撤去対象は本 Q 決定時点で再確認すること（その時点で同様の暫定 `suppress: [RULE-006]` を持つ resolved FND があれば併せて撤去対象に含める）。
- 著作資産への伝播（FND-99 パターン）: FND 接続規則の変更は config.yaml だけでなく verification-author（自身）・接続マトリクス（03-connection-matrix.md）・ドキュメント一覧（01-document-items.md）の FND 行へも同期が必要（決定・実装時に実施）。
- 関連: FND-101（FND-1〜95 の forward 辺残留の是正）は本 Q の決定（FND 専用ライフサイクルルール）に依存する。
