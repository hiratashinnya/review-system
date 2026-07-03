**深刻度**: WARNING

**対応状況**: resolved（解消と同コミットで処置済み・sprint-1。ただし**バックリファレンス対象が未著作のため意図的にエラー発火状態を保持**＝下記「バックリファレンスの扱い」「孤立エラーの意図的保持」を参照）

**改訂理由（z バンプ v0.1→v0.1.1・FND-110/DD-21 適用是正）**:
オーナー決定に従い、resolved FND の辺逆転ルール（DD-3・処置対象→FND の被参照辺へ張り直し・元 forward 辺は削除・指摘時 ref_version は本文へ移動）を本 FND にも適用し、辺の扱いを明確化した。具体的には、(1) v0.1 が残していた元の forward 辺（`→FND-96` ref "0.4"・`→DD-15` ref "0.1"）を削除して `edges: []` とし、指摘時 ref_version は本文の「指摘時 ref_version」節に維持・明確化する。(2) 本 FND の処置対象は 7 つの out-of-graph 著作資産（ノードでない）であり、バックリファレンス（対象→FND-99）の張り先が現時点で存在しないため、FND-99 は outgoing/incoming 辺をともに持たず孤立し、抑制不可（RULE-005＝always_error）のエラーを発火する。(3) **このエラーは恣意的に抑制しない**（`suppress` を付けない）＝「resolved だがバックリファレンス対象が未著作」を正しく示すシグナルとして意図的に保持する旨を本文に明記する。指摘内容・深刻度・対応した同期資産リストは変更しない（forward 辺削除・辺逆転＝lifecycle 操作のため MINOR バンプとして記録していたが、DD-21 の確定原則「resolved-FND の辺逆転/backref 付与は z バンプ」に照らし FND-110 で是正、z バンプへ訂正）。

### 内容

設計層の接続規則を変更する決定（FND-96・DD-15）が、`config.yaml`（機械判定の正本）には反映されているものの、その規則を人間/LLM 向けに表現する out-of-graph の著作資産（スキル・エージェント定義・接続マトリクス等）には伝播していなかった。著作資産が config と食い違ったまま放置されると、次回 design-author がノードを著作する際に**旧ルールの誤った辺を再生産する**。FND-98（DD-13 改訂後のダッシュボード/PR 本文の陳腐化）と同種の「決定の非伝播」ドリフト。

ドリフトしていた規則は2系統:

1. **FND-96（MOD/DM 規則・2026-06-20）**: `MOD → P`（単一）→ 正しくは `MOD → [P | D]`（OR）。`DM → P` → 正しくは `DM → MOD`（DM→MOD→D チェーン）。
2. **DD-15（ORC 規則・2026-06-18）**: `ORC → P` → 正しくは `ORC → E`（起動イベント参照）。architecture-design スキルには反映済みだったが、他の著作資産に未伝播だった。

### 深刻度判定の根拠

`config.yaml`（機械判定の正本）は既に正しいため、検証ツール上の **規則内容に起因する** live な RULE 違反は発生しない（out-of-graph 資産は `trace_scope` 対象外）。一方、著作ガイドが正本と食い違うと誤った辺の再生産を招くため、FND-98 と同じく構造的・運用上のドリフトとして **WARNING**。

> 注: 本 FND が現在発火している RULE-005（完全孤立）エラーは、上記の指摘内容（規則の非伝播・WARNING）とは別物であり、「resolved だがバックリファレンス対象が未著作」という FND ライフサイクル上のシグナルである（下記参照）。深刻度 WARNING は指摘内容そのものの評価であって、孤立エラーの severity（RULE-005＝error・always_error）とは独立である。

### 対応内容

解消と同時起票。以下7資産を `config.yaml` の正ルールに同期（FND-96 の `MOD→[P|D]`／`DM→MOD`、DD-15 の `ORC→E`）:

- `.claude/skills/architecture-design/SKILL.md`（MOD 必須辺）
- `.claude/skills/domain-model/SKILL.md`（DM 必須辺・TERM→SPEC 補正）
- `.claude/skills/orchestration-design/SKILL.md`（ORC 必須辺）
- `.claude/agents/design-author.md`（MOD/ORC/DM 行）
- `.github/agents/design-author.agent.md`（MOD/ORC/DM 行）
- `docs/doc-system/03-connection-matrix.md`（mermaid＋接続要否マトリクス MOD/DM/ORC 行）
- `docs/doc-system/01-document-items.md`（MOD/DM/ORC 上流参照）

> **バックリファレンスの扱い（オーナー決定・v0.2）**: FND-99 の**処置対象は上記7資産（いずれも out-of-graph・ノードでない）**ため、`対象 → FND-99` のバックリファレンス辺を張る先のノードが**現時点では存在しない**。オーナー決定に従い、**設計・実装が進めばこれらの規則を実体化するノード（例: 接続マトリクス・著作ガイドに対応する設計/実装ノード）が著作され、その時点でバックリファレンス対象が生まれる。それまでは恣意的な抑制を行わず、エラー発火状態を保持する**（`suppress` を付けない）。辺逆転ルール（DD-3）に従い、元の forward 辺（`→FND-96`・`→DD-15`）は v0.2 で削除し、指摘時 ref_version は下記「指摘時 ref_version」節に記録する。FND-96・DD-15 は本指摘の subject であって処置対象ではないため、両ノードの版・辺は変更しない（本 FND から両ノードへの forward 辺も張らない）。

> **🔴 孤立エラーの意図的保持（恣意的抑制の禁止）**: 上記の結果、FND-99 は outgoing 辺（forward を削除済み）も incoming 辺（バックリファレンス対象が未著作）も持たず**完全に孤立**し、**RULE-005（完全孤立＝in/out 辺が0本・always_error・抑制不可）のエラーを発火する**。これは欠陥ではなく、**「FND-99 は resolved だが、その処置（規則の著作資産への伝播）を引き受けるべきバックリファレンス対象ノードがまだ著作されていない」という状態を正しく示す意図的なシグナル**である。RULE-005 は always_error（`suppress`・`scheduled`・`activate_stage` いずれでも抑制不可）であり、恣意的に抑制することはできず、またオーナー決定によりすべきでない。設計・実装フェーズで対応するノードが著作され、`対象 → FND-99` のバックリファレンス辺が張られた時点でこの孤立エラーは自然に解消する。それまでは本エラーを**意図的に保持**する。

### 指摘時 ref_version

FND 解消時に辺が逆向きに張り直され（対象→FND）元の forward 辺（FND→対象）が削除されるため、辺情報から指摘時の版が失われる。本文に明記する（DD-3 制度化）。本 FND は処置対象が out-of-graph 資産でバックリファレンス対象が未著作のため辺がすべて失われており、以下が指摘時の版の唯一の証跡である。

- **FND-96 "0.4"**（02-findings.md の FND-96 バッジ v0.4 時点・MOD/DM 規則変更の出所）
- **DD-15 "0.1"**（04-decisions.md の DD-15 バッジ v0.1 時点・ORC 規則変更の出所）
- DD-13 "0.2"（04-decisions.md の DD-13 バッジ v0.2 時点・MOD 粒度 C 案の決定文脈。FND-98 と同コミットで処置した際の関連版）
