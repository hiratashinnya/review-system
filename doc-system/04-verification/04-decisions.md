---
version: "0.1.6"
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
| 生きた義務辺 | PEND-1 → I-1-1 | "0.5" | "0.6" | 更新（PEND-1 は生きた義務辺） |
| forward 辺不一致 | FND-3 → E-1 | "0.4" | E-2 "0.5" に張替え | 更新（E-2 が処置対象ノード） |

**決定**: 推奨案（生きた依存辺のみ一括更新・凍結記録は DD-2 に委ねる）を採用。

**影響範囲**:
- `03-analysis/04-events.md`: E-1・E-2 の ACTOR-1 辺 ref_version 更新 + →DD-4 付与（v0.5.1→0.5.2）。
- `03-analysis/02-io.md`: O-1・O-2 の ACTOR-2 辺 ref_version 更新 + →DD-4 付与（v0.6.1→0.6.2）。
- `04-verification/02-findings.md`: FND-3 の forward 辺を E-2 に張替え・ref_version 更新 + →DD-4 付与、FND-17 を resolved に更新（v0.1.3→0.1.4）。
- `04-verification/03-pend.md`: PEND-1 の I-1-1 辺 ref_version 更新 + →DD-4 付与（v0.1.0→0.1.1）。

---

## DD-5: NFR から SPEC 導出を必須化する

**status: decided**（2026-06-13 反映完了）

<details><summary>⬡ DD-5 · v0.1</summary>

```yaml
id: DD-5
type: DD
labels: []
scheduled: ""
edges:
  - to: FND-26
    ref_version: "0.1"
```
</details>

**論点**: 現状 NFR-1〜NFR-6 の全 6 件に SPEC 依存辺がゼロであり、NFR が達成されたかどうかを機械的に検証できない。FR → SPEC 導出は RULE-017/018 で強制されているが、NFR に同等のルールがなく、NFR は「制約として宣言するだけ」で終わる構造になっている。NFR をテスタブルな仕様として確実に達成可能な形にするには、NFR→SPEC 導出ルールを追加する必要がある。

**選択肢**:
- **A（RULE 追加）**: config.yaml に `must_link_to: NFR → [SPEC]` を追加し、NFR が少なくとも 1 本の SPEC 依存辺を持つことを必須化。NFR-1〜6 に各々 SPEC を導出して接続する。
- **B（suppress 許容）**: A に加えて、定量化困難な NFR（例: NFR-3「self-contained」）は `suppress: [RULE-xxx]` で個別免除を許容する。
- **C（現状維持）**: NFR は抽象制約として保持し、対応 SPEC は FR 側でカバーされているとみなす（検証の網羅穴は許容）。

**推奨**: A + B の組み合わせ。理由：NFR は「非機能」とはいえ機械検証可能な制約（例: NFR-1「プレーンテキスト形式」→ ファイルのバイナリ有無検査 SPEC、NFR-2「標準ライブラリのみ」→ import チェック SPEC）に落とせるものが多い。定量化が難しい NFR は suppress で免除するが理由コメント必須とする。C は検証穴を永続化するため不採用。

**決定**: A + B の組み合わせを採用（N6 処置・2026-06-13）。SPEC-44〜49（NFR-1〜6 各1件・normal）著作・config.yaml の `must_link_to` を `SPEC → [FR, NFR]` に変更・`must_be_linked_from: NFR ← [SPEC]` ルールを requirements ステージで追加・NFR-1〜6 に `→DD-5` バックリファレンス付与を実施した。

**影響範囲（2026-06-13 反映完了）**:
- `config.yaml`（out-of-graph）: `must_link_to` を `SPEC → [FR, NFR]` に変更（SPEC が NFR を直接親にできるよう拡張）。`must_be_linked_from` に `NFR ← [SPEC]`（requirements ステージ・warning）を追加。**番号付き RULE は新設せず config 駆動の被依存辺ルールで実装**（当初提案の「RULE-028 相当」は採らず・RULE-028 は別件のフィールドスキーマ検査に割当）。
- `doc-system/02-what/03-spec.md`: SPEC-44〜49（NFR-1〜6 各1件・normal）を著作。
- `doc-system/02-what/02-nfr.md`: NFR-1〜6 それぞれに `→DD-5` バックリファレンス付与。
- 残作業（未反映）: `.claude/agents/requirements-author.md`・`spec-author.md`・`docs/doc-system/07-authoring-guide.md` への「NFR の SPEC 導出必須」規約追記は今後（著作プロセスへの定着）。

---

## DD-6: 依存グラフレポート出力機能・参照関係複雑度算出の追加

**status: decided**（FR-15/16・SPEC-50/51 著作済み 2026-06-13・残: 分析層（O-4/O-5/P-8/P-9）著作待ち）

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

**決定**: A + C を採用（N8 処置・2026-06-13）。FR-15（依存グラフレポート）・FR-16（複雑度算出）著作・SPEC-50/51 著作（spec 層完了）。分析層（O-4/O-5/P-8/P-9）は設計フェーズで著作予定。

**影響範囲（2026-06-13 spec 層処置完了・分析層以降は今後）**:
- `doc-system/02-what/01-fr.md`: FR-15（依存グラフレポート）・FR-16（複雑度算出）を新設（v0.2.3）。各 FR に `→DD-6` バックリファレンス付与。
- `doc-system/02-what/03-spec.md`: SPEC-50（FR-15 normal）・SPEC-51（FR-16 normal）を著作（v0.3.2）。
- `doc-system/03-analysis/`: 新 O ノード（O-4: 依存グラフ出力・O-5: 複雑度レポート）・新 P ノード（P-8: グラフ出力処理・P-9: 複雑度計算）は未着手（設計フェーズ以降）。

---

## DD-7: 分析層ワークフロー改訂（図と並走してノード著作・D は分析層で起票）＋ DFD 修正の技術決定

**status: decided**（2026-06-13 反映完了）

<details><summary>⬡ DD-7 · v0.1</summary>

```yaml
id: DD-7
type: DD
labels: []
scheduled: ""
edges:
  - to: FND-27
    ref_version: "0.1"
```
</details>

**論点**: 分析層 DFD Level 1 のオーナーレビューで 5 点の指摘が出た。①P-6 の config 直読み、②D の起票タイミング、③プロセス間データの D 化、④P-7 の記載内容入力欠如、⑤分析層ワークフロー（ノードを先に作って図を後付けする順序）。①③④は FND-21/22/23 で処置。本 DD は②⑤のプロセス決定と、③④の D→SPEC 紐付け・新規 ID 採番という技術的選択を記録する。

**決定**:
- **②D の起票タイミング = 分析層（変更なしを確認）**: config.yaml の `must_link_to: D→SPEC / D→P` と `must_be_linked_from: D←P` は既に `activate_stage: analysis` で発火する。機械ルール上 D は分析層ノードとして正しく扱われており、config 変更は不要。欠けていたのは著作運用（D を分析層で起票する手順）であり、`.claude/agents/analysis-author.md`・`.claude/agents/structured-analysis.md` にプロセス間データの D 起票を明示する（資産更新で対応・新規機能 SPEC は起こさない）。
- **⑤分析層ワークフロー = 図と並走してノード著作**: コンテキスト図 → L1 DFD → L2 分解を描きながら、各 ACTOR/I/O/D/P/E ノードを同時に著作・整合させる（図を後付けで起こさない）。structured-analysis エージェントの手順にこの並走を明記する。
- **③D→SPEC 紐付け規約**: 各 D はその生成プロセスを規定する SPEC に紐づける（D-1→SPEC-24 の先例に倣う）。D-3→SPEC-21（設定読込）・D-4→SPEC-1（パース生成物）・D-5→SPEC-2（パース段違反）・D-6→SPEC-5（RULE 検査）・D-7→SPEC-14（カバレッジ）・D-8→SPEC-38（tmp 草案著作）。
- **④新規 ID 採番（退役 ID 不再利用）**: 退役済み ID は再利用しない（再利用すると過去の FND 経緯記述と衝突し追跡性を損なう＝ID 永続原則）。(a) ノード記載内容入力は I-8（FND-10 で「著作エージェント定義」として削除）を再利用せず **I-9** を採番。(b) 設定オブジェクト等の新規 D は D-2（FND-8 で「著作済みノードファイル」として削除・O-3 へ再定義）を再利用せず **D-3** から採番する。I-8・D-2 は欠番＝退役として残す。

**影響範囲（2026-06-13 反映完了）**:
- `doc-system/03-analysis/02-io.md`: D-3〜D-8・I-9 を起票。D-1 に →FND-22 付与。
- `doc-system/03-analysis/03-processes.md`: P-5（D-3 生成元）・P-6（I-5 削除・D-3 消費）・P-1/P-2-*/P-3-*（D-3/D-4 消費）・P-4（D-5/D-6/D-7 消費）・P-7-1（I-9 消費）・P-7-2（D-8 消費）を再配線。P-5/P-6/P-1/P-4/P-7-1/P-7-2 に →DD-7、P-6 に →FND-21、P-7-1 に →FND-23 付与。
- `doc-system/02-what/03-spec.md`: SPEC-54（FR-13・P-7 記載内容入力）新設。
- `doc-system/03-analysis/03-processes.md`: P-5 本文の設定オブジェクト消費先に P-6 を追記（①の経路是正は分析層プロセス設計の修正であり SPEC 変更は不要）。
- `doc-system/03-analysis/00-dfd.md`: Level 1/2 を D ノード経由（P-5→D-3→P-6 等）に再描画。
- `.claude/agents/analysis-author.md`・`.claude/agents/structured-analysis.md`: D の分析層起票・図との並走を明記。
- D-3・I-9 に →DD-7 バックリファレンス付与。
