**深刻度**: WARNING

**対応状況**: resolved（既存 PROMPT ノード4件からの backref 付与で在グラフ化完了・2026-07-21）。従来 v0.1.1 で記していた「バックリファレンス対象が未著作のため意図的にエラー発火状態を保持する」という扱いは**撤回する**（下記「在グラフ化による resolved 化」を参照）。

**改訂理由（z バンプ v0.1.1→v0.1.2・DD-8/DD-21）**:
オーナー決定に従い、FND-99 の処置（設計接続規則の非伝播）を引き受ける在グラフ担体として**既存の PROMPT ノード4件から `PROMPT → FND-99` の backward 辺（backref）を付与**し、FND-99 を在グラフ化して resolved 状態を構造的に充足させた。これにより v0.1.1 が保持していた「完全孤立（RULE-005・always_error）を意図的シグナルとして保持する」という状態は解消された。本改訂は本文改訂＝z バンプ（DD-8/DD-21）。FND-99 自身の edges は空（forward 辺なし＝`fnd_lifecycle.resolved.must_not_link_to` 充足）を維持し、backref は PROMPT 側に張る（別途処置済み）。指摘時 ref_version（FND-96 "0.4"・DD-15 "0.1"）の記録は下記「指摘時 ref_version」節に保持する。

### 内容

設計層の接続規則を変更する決定（FND-96・DD-15）が、`config.yaml`（機械判定の正本）には反映されているものの、その規則を人間/LLM 向けに表現する out-of-graph の著作資産（スキル・エージェント定義・接続マトリクス等）には伝播していなかった。著作資産が config と食い違ったまま放置されると、次回 design-author がノードを著作する際に**旧ルールの誤った辺を再生産する**。FND-98（DD-13 改訂後のダッシュボード/PR 本文の陳腐化）と同種の「決定の非伝播」ドリフト。

ドリフトしていた規則は2系統:

1. **FND-96（MOD/DM 規則・2026-06-20）**: `MOD → P`（単一）→ 正しくは `MOD → [P | D]`（OR）。`DM → P` → 正しくは `DM → MOD`（DM→MOD→D チェーン）。
2. **DD-15（ORC 規則・2026-06-18）**: `ORC → P` → 正しくは `ORC → E`（起動イベント参照）。architecture-design スキルには反映済みだったが、他の著作資産に未伝播だった。

### 深刻度判定の根拠

`config.yaml`（機械判定の正本）は既に正しいため、検証ツール上の **規則内容に起因する** live な RULE 違反は発生しない（out-of-graph 資産は `trace_scope` 対象外）。一方、著作ガイドが正本と食い違うと誤った辺の再生産を招くため、FND-98 と同じく構造的・運用上のドリフトとして **WARNING**。

### 対応内容

解消と同時起票。以下7資産を `config.yaml` の正ルールに同期（FND-96 の `MOD→[P|D]`／`DM→MOD`、DD-15 の `ORC→E`）:

- `.claude/skills/architecture-design/SKILL.md`（MOD 必須辺）
- `.claude/skills/domain-model/SKILL.md`（DM 必須辺・TERM→SPEC 補正）
- `.claude/skills/orchestration-design/SKILL.md`（ORC 必須辺）
- `.claude/agents/design-author.md`（MOD/ORC/DM 行）
- `.github/agents/design-author.agent.md`（MOD/ORC/DM 行）
- `docs/doc-system/03-connection-matrix.md`（mermaid＋接続要否マトリクス MOD/DM/ORC 行）
- `docs/doc-system/01-document-items.md`（MOD/DM/ORC 上流参照）

### 在グラフ化による resolved 化（backref 内訳・4/7 の扱い）

**オーナー決定（既存 PROMPT ノードから backref を付与）に従い、FND-99 を在グラフ化して resolved 化した。** FND-99 はもはや孤立していない——下記4つの PROMPT ノードから被参照（`PROMPT → FND-99` の backward 辺）される。

**直接 backref 付与＝4 PROMPT ノード**（処置対象7資産のうち `.claude/skills/{3}` ＋ `.claude/agents/design-author.md` の在グラフ担体）:

1. `architecture-design` skill プロンプト（MOD 必須辺の著作ガイド担体）
2. `domain-model` skill プロンプト（DM 必須辺の著作ガイド担体）
3. `orchestration-design` skill プロンプト（ORC 必須辺の著作ガイド担体）
4. `design-author` プロンプト（MOD/ORC/DM 行の著作ガイド担体）

**残り3資産の扱い**（直接 backref なしだが論理的に被覆済み）:

- `.github/agents/design-author.agent.md` は `design-author` の Copilot ミラーであり、`design-author` PROMPT ノードで論理被覆される（同一著作ロジックの別プラットフォーム担体）。
- `docs/doc-system/03-connection-matrix.md`・`docs/doc-system/01-document-items.md` は接続規則の記述資産であり、その規則内容は既に CFG `must_link_to`/`must_be_linked_from` ノードおよび SCM `接続ルールスキーマ` ノードで在グラフモデル化済み。規則そのものは在グラフで正本化されているため、記述資産の非伝播は上記モデル化ノード＋4 PROMPT backref で構造的に閉じている。

**resolved 妥当性**: `fnd_lifecycle.resolved.must_be_linked_from` は min-one（source: any）であり、4本の backward 辺（4 PROMPT ノード）で構造的に充足する。したがって FND-99 の resolved 化は妥当である。

### 孤立エラーの解消（恣意的抑制の禁止という思想の維持）

v0.1.1 では、処置対象7資産がいずれも out-of-graph（ノードでない）でバックリファレンス対象が未著作だったため、FND-99 は in/out 辺をともに持たず完全孤立し、RULE-005（always_error・抑制不可）を発火していた。当時は「resolved だがバックリファレンス対象が未著作」というシグナルを恣意的に抑制せず意図的に保持していた。

**恣意的抑制の禁止という思想は引き続き正しい**——孤立エラーを `suppress` 等で握りつぶすべきではない。ただし本改訂では、その孤立を**抑制ではなく実際の解消によって消した**。オーナー決定に従い既存 PROMPT ノード4件から backref を付与したことで、FND-99 は在グラフの被参照ノードとなり、孤立（RULE-005）は自然に解消された。すなわち「エラーを保持し続ける」のではなく「エラーの根本原因（在グラフ担体の不在）を解消した」点が v0.1.1 からの実質的な変化である。

### 指摘時 ref_version

FND 解消時に辺が逆向きに張り直され（対象→FND）元の forward 辺（FND→対象）が削除されるため、辺情報から指摘時の版が失われる。本文に明記する（DD-3 制度化）。本 FND は forward 辺を持たず（処置対象が out-of-graph 資産で、在グラフ担体は subject でなく別途 PROMPT ノード側から被参照）、以下が指摘時の版の唯一の証跡である。

- **FND-96 "0.4"**（02-findings.md の FND-96 バッジ v0.4 時点・MOD/DM 規則変更の出所）
- **DD-15 "0.1"**（04-decisions.md の DD-15 バッジ v0.1 時点・ORC 規則変更の出所）
- DD-13 "0.2"（04-decisions.md の DD-13 バッジ v0.2 時点・MOD 粒度 C 案の決定文脈。FND-98 と同コミットで処置した際の関連版）
