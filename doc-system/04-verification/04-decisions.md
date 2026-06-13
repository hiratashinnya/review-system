---
version: "0.1.2"
---
# 意思決定 — Decision Log

> **型**: DD ／ 義務辺（DD→X）が存在する間は「未反映」で RULE-001 ERROR。反映後は辺を削除し、影響を受けたノード側に X→DD を張る（経緯の永続記録）。
> DD は無名依存辺のみ（`kind`/`status` なし・`to` は単数・`ref_version` 必須）。ライフサイクルは本文の status バッジに記載。

---

## DD-1: SR-4 を SR-2 の重複として削除し被依存を SR-2 へ再配線

**status: decided**（2026-06-12 反映完了）

<details><summary>⬡ DD-1 · v0.1</summary>

```yaml
id: DD-1
type: DD
labels: []
scheduled: ""
edges: []
```
</details>

**論点**: 旧 SR-4「spec-inspector がノードをパースして RULE を評価できるマシンリーダブルな形式を求める」は、ステークホルダー要求（SR）として妥当か。主語が spec-inspector＝**系そのもの**であり、他の SR（著者・レビュアー・メンテナの欲求）と粒度が揃っていない。FND-1（ACTOR-3 を外部 ACTOR にした系境界誤り）の根因でもある。

**選択肢**:
- A. SR-4 を削除し、被依存（FR-1/FR-9/NFR-1/NFR-2/NFR-6）を SR-2 へ再配線。形式制約は既存 NFR-1/2/6 が表現済みのため新 NFR は作らない。
- B. SR-4 を削除し、新 NFR-7「マシンリーダブルな構造化形式」を明示新設して再配線。

**推奨**: A。SR-4 は **SR-2「レビュアーが機械的に網羅性・整合性を検証できる」を“系の視点”で言い換えた重複**であり、マシンリーダブル形式という制約は既に NFR-1（プレーンテキスト）・NFR-2（標準ライブラリでパース可能）・NFR-6（ライフサイクルを型で判定）が表現している。B は NFR-1/2/6 と重複する umbrella NFR を生む。

**決定**: A を採用（オーナー承認・2026-06-12）。

**影響範囲**:
- `01-why/02-sr.md`: SR-4 削除（墓碑コメントを残す）。version 0.2.0→0.2.1（z バンプ＝x.y 据え置きで依存辺のドリフトを誘発しない）。
- `02-what/01-fr.md`: FR-1（ノードグラフの構造化表現）・FR-9（トレース対象集合の宣言）を `→SR-4` から `→SR-2` へ再配線。各ノードに `→DD-1` を付与。
- `02-what/02-nfr.md`: NFR-1（プレーンテキスト形式）・NFR-2（標準ライブラリでパース可能）・NFR-6（ライフサイクルを型で判定）を `→SR-4` から `→SR-2` へ再配線。各ノードに `→DD-1` を付与。
- 分析層への波及: 旧 SR-4 を指していた ACTOR-3 は FND-1 で削除済み。他に SR-4 参照ノードはなく、分析層（ACTOR/I/O/D/P/E）の辺は不変。

---

## DD-2: VERIFY の RULE-004 免除・FND は再検証シグナルとして据え置き（Q-1 から昇格）

**status: decided**（2026-06-13 反映完了）

<details><summary>⬡ DD-2 · v0.1</summary>

```yaml
id: DD-2
type: DD
labels: []
scheduled: ""
edges: []
```
</details>

**論点**: VERIFY ノードや解消済み FND など「ある時点の状態をレビュー/指摘した凍結記録」の ref_version は、参照先ファイルが版上げされるたびに RULE-004 ドリフト WARNING を発火し続ける。（Q-1 より昇格）

**選択肢**:
- **A（VERIFY 免除）**: VERIFY に `suppress: [RULE-004]` を付与し、凍結スナップショットとして RULE-004 を免除。
- **B（都度更新）**: 記録系も生きた依存辺として ref_version を最新化。実際にはレビューしていない版を指す矛盾が生じうる。
- **C（シグナル据え置き）**: ドリフト発火を再検証シグナルとして活用し、陳腐化したら新 VERIFY/FND を起票。

**決定**:
- **VERIFY ノード**: A を採用。`suppress: [RULE-004]` を付与し「過去の検証事実スナップショット」として凍結。理由：VERIFY は「いつ・何の版を・どのようにレビューしたか」の過去事実であり、参照先の将来変更で書き換えると証跡として不正確になる。本文に実施日・対象版を記載することを前提とする。
- **FND（解消済み含む）**: C を採用。ドリフト発火を「記録が陳腐化→再検証を検討」のシグナルとして活用する。辺逆転後（target→FND）もドリフト発火は有効な再検証シグナルとなる。

**影響範囲**:
- `04-verification/01-doc-verify.md`: VERIFY-1・VERIFY-2 に `suppress: [RULE-004]` を付与（v0.1.1→0.1.2）。各ノードに `→DD-2` バックリファレンス辺を付与。
- `04-verification/05-questions.md`: Q-1 を `status: closed`（DD-2 へ昇格済み）に更新（v0.1.0→0.1.1）。

---

## DD-3: FND 起票時の ref_version 本文記録ルール制度化

**status: decided**（2026-06-13 反映完了）

<details><summary>⬡ DD-3 · v0.1</summary>

```yaml
id: DD-3
type: DD
labels: []
scheduled: ""
edges: []
```
</details>

**論点**: FND 解消時に edges が「FND→対象」から「対象→FND」へ逆転するため、元の指摘時の `ref_version`（どの版の対象を指摘したか）が辺情報から失われる。

**選択肢**:
- **A（本文明記ルール）**: FND 起票時に `edges[].ref_version` の値を本文にも明記。実装コストゼロ・プロセス追加のみ。
- **B（専用属性追加）**: FND ノードに `target_ref_version` 等の専用属性を追加。スキーマ拡張コスト大・既存 FND の遡及修正が発生。
- **C（バックリファレンス辺の ref_version を使う）**: target→FND 辺の ref_version に「処置時の版」を記録。辺の意味論（指摘時の版→処置時の版）が変わり混乱を招く。

**決定**: A を採用。FND 起票時に `edges[].ref_version` 値を本文に明記することを制度化。記録形式：
```
**指摘時 ref_version**: {ノードID} "{ref_version 値}"（{ファイル名} v{version} 時点）
```

**影響範囲**（すべてグラフ外プロセスドキュメント・in-graph 義務辺不要）:
- `.claude/agents/verification-author.md`: FND 著作ルールに本文記録ルールを追加。
- `docs/doc-system/07-authoring-guide.md`: FND 解消ライフサイクルセクションに追記。
- `.claude/skills/spec-principles/SKILL.md`: PR7 関連のバックリファレンス規律に注記追加。
- `CLAUDE.md`: 「判断の仰ぎ方」セクションのバックリファレンス規律に注記追加。

---

## DD-4: 分析層 ref_version ドリフト群の一括解消（FND-17 から昇格）

**status: decided**（2026-06-13 反映完了）

<details><summary>⬡ DD-4 · v0.1</summary>

```yaml
id: DD-4
type: DD
labels: []
scheduled: ""
edges: []
```
</details>

**論点**: FND-17（findings.md）で追跡していた分析層 ref_version ドリフト群を正式な意思決定として記録し、「生きた依存辺」を一括解消する。凍結記録（VERIFY-1・解消済み FND-2/FND-4）は DD-2 に委ねる。

**ドリフト群の整理**:

| 区分 | 辺 | 現 ref_version | 更新後 | 決定 |
|---|---|---|---|---|
| 生きた依存辺 | E-1 → ACTOR-1 | "0.2" | "0.3" | 更新 |
| 生きた依存辺 | E-2 → ACTOR-1 | "0.2" | "0.3" | 更新 |
| 生きた依存辺 | O-1 → ACTOR-2 | "0.2" | "0.3" | 更新 |
| 生きた依存辺 | O-2 → ACTOR-2 | "0.2" | "0.3" | 更新 |
| 凍結記録 VERIFY-1 | VERIFY-1 → ACTOR-1/I-1/P-1/E-1 | "0.2"/"0.4" | 据え置き | DD-2（suppress[RULE-004]）に委ねる |
| 解消済み FND-2 | FND-2 → P-2 | "0.5" | 据え置き | DD-2（再検証シグナル）に委ねる |
| 解消済み FND-4 | FND-4 → P-3 | "0.5" | 据え置き | DD-2 に委ねる |
| 生きた義務辺 | PEND-1 → I-2 | "0.5" | "0.6" | 更新（PEND-1 は生きた義務辺） |
| forward 辺不一致 | FND-3 → E-1 | "0.4" | E-2 "0.5" に張替え | 更新（E-2 が処置対象ノード） |

**決定**: 推奨案（生きた依存辺のみ一括更新・凍結記録は DD-2 に委ねる）を採用。

**影響範囲**:
- `03-analysis/04-events.md`: E-1・E-2 の ACTOR-1 辺 ref_version 更新 + →DD-4 付与（v0.5.1→0.5.2）。
- `03-analysis/02-io.md`: O-1・O-2 の ACTOR-2 辺 ref_version 更新 + →DD-4 付与（v0.6.1→0.6.2）。
- `04-verification/02-findings.md`: FND-3 の forward 辺を E-2 に張替え・ref_version 更新 + →DD-4 付与、FND-17 を resolved に更新（v0.1.3→0.1.4）。
- `04-verification/03-pend.md`: PEND-1 の I-2 辺 ref_version 更新 + →DD-4 付与（v0.1.0→0.1.1）。

---

## DD-5: NFR から SPEC 導出を必須化する

**status: open**（影響範囲調査中・反映未完了）

<details><summary>⬡ DD-5 · v0.1</summary>

```yaml
id: DD-5
type: DD
labels: []
scheduled: ""
edges:
  - to: NFR-1
    ref_version: "0.2"
  - to: NFR-2
    ref_version: "0.2"
  - to: NFR-3
    ref_version: "0.2"
  - to: NFR-4
    ref_version: "0.2"
  - to: NFR-5
    ref_version: "0.2"
  - to: NFR-6
    ref_version: "0.2"
```
</details>

**論点**: 現状 NFR-1〜NFR-6 の全 6 件に SPEC 依存辺がゼロであり、NFR が達成されたかどうかを機械的に検証できない。FR → SPEC 導出は RULE-017/018 で強制されているが、NFR に同等のルールがなく、NFR は「制約として宣言するだけ」で終わる構造になっている。NFR をテスタブルな仕様として確実に達成可能な形にするには、NFR→SPEC 導出ルールを追加する必要がある。

**選択肢**:
- **A（RULE 追加）**: config.yaml に `must_link_to: NFR → [SPEC]` を追加し、NFR が少なくとも 1 本の SPEC 依存辺を持つことを必須化。NFR-1〜6 に各々 SPEC を導出して接続する。
- **B（suppress 許容）**: A に加えて、定量化困難な NFR（例: NFR-3「self-contained」）は `suppress: [RULE-xxx]` で個別免除を許容する。
- **C（現状維持）**: NFR は抽象制約として保持し、対応 SPEC は FR 側でカバーされているとみなす（検証の網羅穴は許容）。

**推奨**: A + B の組み合わせ。理由：NFR は「非機能」とはいえ機械検証可能な制約（例: NFR-1「プレーンテキスト形式」→ ファイルのバイナリ有無検査 SPEC、NFR-2「標準ライブラリのみ」→ import チェック SPEC）に落とせるものが多い。定量化が難しい NFR は suppress で免除するが理由コメント必須とする。C は検証穴を永続化するため不採用。

**影響範囲（調査後に確定・現在は義務辺として開放）**:
- `config.yaml`（out-of-graph）: `rule_activation` に NFR SPEC 必須化ルール（RULE-028 相当）を追加。`must_link_to` に `NFR → [SPEC]` を追加。
- `docs/doc-system/05-verification.md`: 新ルール定義を追記。
- `doc-system/02-what/02-nfr.md`: NFR-1〜6 それぞれに SPEC 導出（内容と suppress 要否は個別判断）→ 各 NFR に `→DD-5` バックリファレンス付与。
- `.claude/agents/requirements-author.md`・`spec-author.md`・`docs/doc-system/07-authoring-guide.md`: NFR の SPEC 導出必須規約を追記。

---

## DD-6: 依存グラフレポート出力機能・参照関係複雑度算出の追加

**status: open**（FR 著作待ち・設計フェーズ）

<details><summary>⬡ DD-6 · v0.1</summary>

```yaml
id: DD-6
type: DD
labels: []
scheduled: ""
edges: []
```
</details>

**論点**: 現行の spec-inspector は RULE 違反レポート（O-1）とカバレッジ点検結果（O-2）のみを出力し、ドキュメント間の依存構造そのものを可視化する機能がない。大規模なノードグラフにおいて特定ノードへの依存集中・孤立・循環参照などが検出困難であり、設計の意思決定支援が不足している。

**追加機能（2本立て）**:
- **依存グラフレポート（②）**: 全ノード間の依存関係を構造化出力する。dot 形式 / 隣接リスト形式等でエクスポートし、外部ツール（Graphviz 等）との連携を可能にする。
- **参照関係複雑度算出（②'）**: 各ノードの in-degree（被参照数）・out-degree（参照数）・入出力比・ファイルをまたぐ参照クラスタ数などを集計し、複雑度メトリクスとして出力する。「ハブノード」「孤立クラスタ」「循環参照候補」を検出する。

**選択肢**:
- **A（新 FR 2 本）**: FR-15「依存グラフレポート出力」・FR-16「参照関係複雑度算出」として独立 FR 化。それぞれ SPEC → P → O の経路を完全に持つ。
- **B（FR-3 拡張）**: FR-3（カバレッジ点検）配下の SPEC として折り込む。粒度的には FR-3 の「グラフ網羅性点検」の延長線上にある。
- **C（post-MVP 印）**: 機能を追加するが `labels: [post-mvp]` で MVP スコープ外とし、設計フェーズまで詳細を先送りする。

**推奨**: A + C の組み合わせ（FR として正式追加 + post-mvp 印）。理由：グラフ可視化と複雑度算出は FR-3（RULE 違反検査）とは目的が異なり独立価値がある（意思決定支援）。ただし MVP には不要のため post-mvp 印で設計フェーズで詳細化。

**影響範囲（FR 著作後に義務辺として反映）**:
- `doc-system/02-what/01-fr.md`: FR-15（依存グラフレポート）・FR-16（複雑度算出）を新設。SR への依存辺、`labels: [post-mvp]`。
- `doc-system/03-analysis/`: 新 O ノード（O-4: 依存グラフ出力・O-5: 複雑度レポート）・新 P ノード（P-8: グラフ出力処理・P-9: 複雑度計算）を追加。
- 設計フェーズで凍結セット（MOD/PORT/DM）へ落とし込む。
