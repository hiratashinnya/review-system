**status: decided**（2026-06-21 オーナー承認・選択肢A 採用）

> **辺の扱い**: 本 DD は decided。影響を受けたノード（Q-4）は処置側から `→DD-16` を張り返す（Q-4 v0.2 で付与）。FND-96/97/98/100 は本 DD で resolved 化されるが、**新 `fnd_lifecycle` ルールにより resolved FND は forward 辺を持てない**（`must_not_link_to`・後述）ため、`→DD-16` は付与せず、本 DD との関連は各 FND の改訂理由本文に記録する（provenance）。config.yaml・著作資産は out-of-graph のため in-graph 義務辺は不要。したがって本 DD の `edges: []`。
> **指摘時 ref_version の記録（DD-3 制度）**: 本 DD は Q-4 から昇格（DD であり FND でない）ため「指摘時 ref_version」の本文記録は不要。

**論点**（Q-4 より昇格・要約）: FND の必須接続は現状、汎用ルール `{ node: FND, target: any }`（config.yaml L60・通称 RULE-006）で代用されている。これは FND 固有のライフサイクル——**未解消＝対象要素を指す（forward 辺）／解消＝処置対象要素から指される（backward 辺）という辺の向きの逆転**——を汎用の依存辺ルールで無理に表現しており、resolved FND が forward 辺を残すか `suppress: [RULE-006]` で抑制するかの歪みを生む。FND 専用のライフサイクルルールを汎用 RULE-006 から独立定義すべきか。

**選択肢**（Q-4 より要約）:
- **選択肢A（FND 専用ライフサイクルルールを config に独立定義・状態依存の必須辺）**: 汎用 `{ node: FND, target: any }` を FND の対応状況に依存する専用ルールへ置換。FND の状態（未解消／resolved）を機械判定可能な専用フィールドに格上げし、(1) 未解消 FND は forward 必須、(2) resolved FND は backward 必須かつ forward 不在期待、という状態別ルールを定義する。機械判定（状態別必須辺）と運用ルール（処置時に forward を消し ref_version を本文へ移す手順）は PR2 に従い分離する。
- **選択肢B（運用ルールのみで担保・config 据え置き）**: config は変更せず `suppress: [RULE-006]` 運用を正式化。機械判定と運用の混在（PR2 違反）が残るため非推奨。
- **選択肢C（現状維持・暫定措置を恒久化）**: forward 残し系と suppress 系の二分を放置。歪みの恒久化で非推奨。

**推奨**: 選択肢A（Q-4 推奨どおり）。

**決定**: **選択肢A を採用**（オーナー承認・2026-06-21）。以下 3 点を実施する。

1. **config.yaml の FND ルール置換**: 汎用 `{ node: FND, target: any }`（must_link_to・L60）を削除し、FND の対応状況（`resolved` フィールド）に依存する専用 `fnd_lifecycle` セクションへ置換する。
   - `resolved_field: resolved`（機械判定の根拠フィールド）
   - **未解消（resolved: false / 未設定）**: `must_link_to: FND → any`（forward 辺必須・verification ステージ・severity error・RULE-006 後継）——「未解消 FND は指摘対象要素を指す」。
   - **resolved（resolved: true）**: `must_be_linked_from: FND ← any`（backward 辺必須・verification ステージ・severity error）——「resolved FND は処置対象要素から指される」。かつ `must_not_link_to: FND → any`（forward 辺の不在期待・verification ステージ・severity warning）——「resolved FND の元 forward 辺は削除済みであること（辺逆転ルール DD-3）」。
2. **FND YAML に `resolved: true/false` フィールドを追加**: FND の対応状況を本文バッジ／散文から機械判定可能なメタ属性へ格上げする。これにより `fnd_lifecycle` の状態分岐が機械的に評価可能になる。
3. **暫定 `suppress: [RULE-006]` の撤去**: 専用ルール導入で代用が不要となった FND-96/97/98/100 の `suppress: [RULE-006]` を撤去し、`resolved: true` を付与する（撤去しなければ抑制の死蔵となる）。これらは別ファイル差分（`tmp/sprint-1/FND-96-100.md`）で出力。本 DD 決定時点で同様の暫定 `suppress: [RULE-006]` を持つ resolved FND を再確認し、対象は FND-96/97/98/100 の 4 件（FND-99 は out-of-graph 処置対象で RULE-005 を意図保持しており `suppress: [RULE-006]` を持たないため対象外）。

**機械判定と運用ルールの分離（PR2）**:
- 機械判定（config の機構）: `fnd_lifecycle` の状態別必須辺（未解消＝forward／resolved＝backward＋forward 不在）。
- 運用ルール（verification-author / reconciliation の手順）: 処置完了時に forward 辺を削除し、処置対象側に `→FND-x` を張り、指摘時 ref_version を本文へ移す手順（DD-3）。後者は config に詰めず手順として残す。

**影響範囲（選択肢A 採用時）**:

機械判定の正本（config.yaml）:
- `docs/doc-system/config.yaml`（out-of-graph）: `must_link_to` から `{ node: FND, target: any, ... }`（L60）を削除し、新 `fnd_lifecycle` セクション（resolved_field / unresolved.must_link_to / resolved.must_be_linked_from / resolved.must_not_link_to）を新設。検証ロジック（パーサ・ルールエンジン）は `resolved` フィールドの判定と状態別ルール分岐を実装（設計層への波及・実装フェーズ）。

in-graph ノード（別ファイル差分で出力）:
- `doc-system/04-verification/02-findings.md`: FND-96（v0.4→0.5）・FND-97（v0.1→0.2）・FND-98（v0.1→0.2）・FND-100（v0.1→0.2）の `suppress: [RULE-006]` 撤去・`resolved: true` 追加（→ `tmp/sprint-1/FND-96-100.md`）。
- `doc-system/04-verification/05-questions.md`: Q-4 を `status: closed`（DD-16 へ昇格）・`→DD-16` 付与・MINOR バンプ v0.1→v0.2（→ `tmp/sprint-1/Q-4.md`）。

**接続規則変更を伴う DD のため、out-of-graph 著作資産への同期が必要**（FND-99 パターン・本 DD は FND の `must_link_to` を `fnd_lifecycle` 状態別ルールへ変更する接続規則変更を含む）。変更型＝FND。下記資産の FND 行を `fnd_lifecycle`（未解消＝forward／resolved＝backward・forward 不在）へ同期する（reconciliation 反映後に主文脈／実装フェーズで実施。本 DD はその同期対象リストを記録する）:

- `docs/doc-system/03-connection-matrix.md`（mermaid 図 `FND --> 任意要素`・接続要否マトリクスの FND 行を状態別表記へ更新）
- `docs/doc-system/01-document-items.md`（FND の上流参照列「→ 指摘対象要素」を未解消／resolved の状態別表記へ更新）
- `.claude/agents/verification-author.md`・`.github/agents/verification-author.agent.md`（FND 行の必須依存辺・FND 解消ライフサイクルの記述を `fnd_lifecycle` ベースへ更新。resolved 時は forward 不在＋backward 必須が機械判定で強制される旨・`resolved` フィールドの記載を追加）

> **同期の確認状況**: 上記は本 DD の処置で同期すべき資産リスト（変更型 FND に対応する接続マトリクス・ドキュメント一覧・verification-author 自身）。本ファイルは reconciliation 用の差分出力（ノード著作）のため、out-of-graph 資産の実ファイル編集は reconciliation 反映後／実装フェーズで実施する（DD-15・FND-99 と同じ別パス運用）。同期完了時に各資産の更新を本 DD 影響範囲のチェック済みとして追記すること。

**関連・後続**: FND-101（FND-1〜95 の forward 辺残留の是正）は本 DD 決定（FND 専用ライフサイクルルール＝resolved 時 forward 不在期待）に依存するが、対象範囲が広く別ブランチ・別スプリントでの実施を要する。**実施スプリントはオーナー判断**（独断でのスプリント繰越は禁止＝CLAUDE.md「スケジュール独断禁止」。FND-101 の `scheduled` は空のままとし判断を仰ぐ）。

**覆る場合の影響範囲**: 選択肢B（運用ルールのみ）／C（現状維持）へ戻す場合、config.yaml の `fnd_lifecycle` を撤去し汎用 `{ node: FND, target: any }` を復元、FND-96/97/98/100 に `suppress: [RULE-006]` を復活させ `resolved` フィールドを撤去、上記 out-of-graph 資産の FND 行を旧表記へ戻す（影響は config・verification 層 FND ノード 4 件・著作資産に限定）。
