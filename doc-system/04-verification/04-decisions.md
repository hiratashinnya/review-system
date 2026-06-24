# 意思決定 — Decision Log

> **型**: DD ／ 義務辺（DD→X）が存在する間は「未反映」で RULE-001 ERROR。反映後は辺を削除し、影響を受けたノード側に X→DD を張る（経緯の永続記録）。
> DD は無名依存辺のみ（`kind`/`status` なし・`to` は単数・`ref_version` 必須）。ライフサイクルは本文の status バッジに記載。
> **影響範囲のバージョン注記**（例：`spec.md v0.3.0→0.3.1`）は**決定時点のスナップショット**（DD-2 凍結記録設計）。現時点のファイル版との差異はドリフトではなく当該 DD 以降の追加変更による自然な版上げを示す（FND-31）。

---

## DD-1: SR-4 を SR-2 の重複として削除し被依存を SR-2 へ再配線

**status: decided**（2026-06-12 反映完了）

<details><summary>⬡ DD-1 · v0.1.0</summary>

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

<details><summary>⬡ DD-2 · v0.1.0</summary>

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

<details><summary>⬡ DD-3 · v0.1.0</summary>

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

<details><summary>⬡ DD-4 · v0.1.0</summary>

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

<details><summary>⬡ DD-5 · v0.1.0</summary>

```yaml
id: DD-5
type: DD
labels: []
scheduled: ""
edges:
  - to: FND-26
    ref_version: "0.1"
  - to: FND-31
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

**status: decided**（FR-15/16・SPEC-50/51 著作済み 2026-06-13・分析層 O-4/O-5/P-8/P-9 著作・反映完了 2026-06-15／N8）

<details><summary>⬡ DD-6 · v0.1.0</summary>

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

**決定**: A + C を採用（N8 処置・2026-06-13）。FR-15（依存グラフレポート）・FR-16（複雑度算出）著作・SPEC-50/51 著作（spec 層完了）。分析層（O-4/O-5/P-8/P-9）は当初設計フェーズ著作予定としたが、N1（current_stage→analysis 進行・2026-06-15）に伴い analysis フェーズで著作・反映完了（下記影響範囲・FND-92 で E-1 整合）。

**影響範囲（2026-06-13 spec 層処置完了・2026-06-15 分析層補完完了／N8）**:
- `doc-system/02-what/01-fr.md`: FR-15（依存グラフレポート）・FR-16（複雑度算出）を新設（v0.2.3）。各 FR に `→DD-6` バックリファレンス付与。
- `doc-system/02-what/03-spec.md`: SPEC-50（FR-15 normal）・SPEC-51（FR-16 normal）を著作（v0.3.2）。
- `doc-system/03-analysis/02-io.md`: O-4（依存グラフ出力ファイル）・O-5（参照関係複雑度メトリクスレポート）を著作（labels: post-mvp・scheduled: sprint-2・各 `→DD-6` 付与）。
- `doc-system/03-analysis/03-processes.md`: P-8（依存グラフ出力処理）・P-9（参照関係複雑度計算処理）を著作（labels: post-mvp・scheduled: sprint-2・各 `→DD-6` 付与）。
- `doc-system/03-analysis/04-events.md`: E-1（点検要求）本文を改訂（DD-8 §4 z バンプ・可視バッジ v0.5 据置・伝播なし）。`--export-graph`→P-8／`--complexity`→P-9 の追加実行・O-4/O-5 追加出力を反映（FND-92 処置）。
- `doc-system/04-verification/02-findings.md`: FND-92（E-1 本文不整合・INFO・resolved）を起票。

---

## DD-7: 分析層ワークフロー改訂（図と並走してノード著作・D は分析層で起票）＋ DFD 修正の技術決定

**status: decided**（2026-06-13 反映完了）

<details><summary>⬡ DD-7 · v0.1.0</summary>

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

---

## DD-8: ノードバッジをノード固有バージョン（x.y.z）に正式化・ファイルフロントマター version 廃止

**status: decided**（2026-06-14 オーナー判断確定）

<details><summary>⬡ DD-8 · v0.1.1</summary>

```yaml
id: DD-8
type: DD
labels: []
scheduled: ""
suppress: []
edges:
  - to: FND-36
    ref_version: "0.1"
  - to: FND-32
    ref_version: "0.1"
  - to: FND-39
    ref_version: "0.1"
  - to: FND-107
    ref_version: "0.1"
```
</details>

**論点**: FND-36 により、ノードバッジ `⬡ FR-1 · v0.3` の `v0.3` が「著作時点のファイル x.y スナップショット」（FND-32 の処置で定義した意味）でも「現在のファイル x.y」でもなく、**ノード固有の改訂回数**を実態として示していることが判明した。FND-32 の処置（notation.md に「バッジ＝ファイル x.y スナップショット」と追記）は実態と乖離した誤定義であり、是正が必要。バッジを正式なノードバージョンとして制度化し、ファイルフロントマターの `version:` を廃止することで、ノード追跡性を一貫した形で高める。

**選択肢**:
- **A（ノード固有リビジョン正式化）**: バッジ＝ノード固有の x.y.z バージョン（MAJOR.MINOR.PATCH）として正式化。`notation.md` の説明文のみ修正。全ノードのバッジ値はそのまま有効で移行作業なし。実態に合致し修正コスト最小。
- **B（ファイル x.y 統一）**: バッジ＝現在のファイル x.y に一致させるため全ノードのバッジを一括修正。大量修正が発生し、ノード改訂履歴の情報（例: FR-1 が 0.3 まで改訂された事実）が失われる。
- **C（バッジ廃止）**: バッジを廃止し `ref_version` のみを版管理の真実源とする。大規模変更が必要で可視性が低下する。

**推奨**: A ベースで拡張。ノードバージョンをファイルフロントマターから独立させ、各ノード固有の x.y.z 体系に正式化する。ファイルフロントマター `version:` は廃止。B は修正コスト大・ノード改訂履歴の消失を招き不採用。C は可視性低下のため不採用。

**決定: A ベースで拡張**（オーナー・2026-06-14）

1. **バッジのノードバージョン正式化**: `⬡ PREFIX-N · vX.Y.Z` の `X.Y.Z` はノード固有バージョン（MAJOR.MINOR.PATCH）として正式化する。現在のバッジ値はすべてそのまま有効（FND-107 処置で x.y → x.y.0 移行済み）。
2. **ファイルフロントマター `version:` 廃止**: 各ファイルの `---\nversion: "x.y.z"\n---` フィールドは廃止する（2026-06-14 全ファイルから削除完了）。新規ファイルへの記載は行わない。
3. **`ref_version` 参照先変更**: `ref_version` は従来のファイル x.y ではなく、参照先ノードのノードバージョン x.y を指すものとして意味論を変更する。全辺の移行を 2026-06-14 に実施済み（VERIFY ノードの凍結辺＝`01-doc-verify.md`・DD-2 suppress[RULE-004] を除く）。
4. **バンプルール**:
   - 構造変更（YAML キー追加・型変更・辺の追加/削除/変更）→ MINOR バンプ（x.Y）
   - 内容のみ（本文修正・バックリファレンス辺追加・suppress 追加）→ z バンプ（x.y.Z）
   - 大規模構造変更（ノード分割・統合・型変更）→ MAJOR バンプ（X.y.z）
   - z バンプは伝播不要（依存元ノードの ref_version 更新不要）
5. **本 DD 適用時の制約**: 今回のノードバージョン改訂は z バンプのみ・伝播させない（本 DD 起因の改訂で大規模な ref_version 更新を誘発しない）。ref_version の一括移行（下記）は「ファイル x.y → ノード x.y」の座標系再表現であり、ノードバージョンの改訂ではない（バッジは不変）。

**影響範囲（2026-06-14 即時実施完了・sprint-2 への繰り越しはオーナー指示により撤回）**:
- `docs/doc-system/04-notation.md`（out-of-graph・直接更新）: §1/§2/§5/§8 のバッジ・フロントマター説明をノード固有バージョン（MAJOR.MINOR.PATCH）に更新。FND-32 の処置（「ファイル x.y スナップショット」定義）を上書き訂正。✅ 完了
- `docs/doc-system/02-meta-schema.md`（out-of-graph）: §1「ファイルバージョニング」を「ノードバージョニング」に書き換え、§7 ドリフト定義・RULE-004 表を「参照先ノードのバッジ x.y」基準に更新。✅ 完了
- `docs/doc-system/05-verification.md`（out-of-graph）: 段階①ドリフト検出・RULE-004 の判定基準を「参照先ノードのバッジ x.y」に更新、トリガを「ノードバッジの版上げ」に変更。✅ 完了
- `docs/doc-system/config.yaml`（out-of-graph）: 冒頭に DD-8 注記（版管理単位＝ノードバッジ・RULE-004 はノード x.y 基準）を追記。✅ 完了
- **全ノードのバッジ値**: 不変（移行作業なし）。✅
- **全辺の `ref_version`**: ファイル x.y → 参照先ノードのバッジ x.y へ一括移行（live 辺 170 件更新・ドリフト 0 を検証）。VERIFY 凍結辺は DD-2 により据え置き。✅ 完了
- **ファイルフロントマター `version:` 削除**: doc-system 配下・docs/doc-system 配下（テンプレート群含む）全ファイルから削除完了。✅ 完了
- **既知の残存事項（履歴保全・PR8）**: 解消済み FND 本文の `**指摘時 ref_version**:` 記録は当時のファイル x.y を凍結記録したものであり、遡及書き換えは provenance を損なうため実施しない（過去の系の下での記録として保持）。新規 FND は DD-3 の様式でノード x.y を記録する。
- ※以下は当初起票時の実施計画（実施済み確認記録）: `doc-system/04-verification/02-findings.md` の FND-36 を `open` → `resolved` に更新し、本 DD（DD-8）を処置記録として明記。FND-32 の処置誤謬（「ファイル x.y スナップショット」定義）が本 DD により是正済みである旨を FND-32 本文に追記。✅ 完了（FND-39 で指摘の旧版残骸行を削除済み）
- **FND-107 是正（2026-06-23）**: 本 DD §1 が「MAJOR.MINOR（2 部）」と誤記し x.y.z バッジの z-bump 機構を機能不能にしていた。FND-107 処置（Case A）により全511ノードのバッジを x.y → x.y.0 に移行し、§1 記述を「MAJOR.MINOR.PATCH（3 部）」に訂正（FND-107 resolved）。

---

## DD-9: config.yaml phases から post-mvp 除去・RULE-029 新設

**status: decided**（2026-06-14 反映完了）

<details><summary>⬡ DD-9 · v0.1.0</summary>

```yaml
id: DD-9
type: DD
labels: []
scheduled: ""
suppress: []
edges:
  - to: FND-78
    ref_version: "0.1"
```
</details>

**指摘時 ref_version**: FND-78 "0.1"（findings.md v0.1 時点）

**論点**: FND-78 で指摘。`config.yaml` の `phases` に `post-mvp` が含まれており、SPEC-28/40 が `scheduled: "post-mvp"` を使用、SPEC-50/51 は `labels: [post-mvp]` だが `scheduled: ""` と表現が不統一。`scheduled` の値ドメインが phases と独立しており、phases 外の文字列を無効化するルールが存在しなかった。

**選択肢**:
- **A（post-mvp 除去＋RULE 新設）**: `phases` から `post-mvp` を除去し、RULE-029「scheduled が非空かつ phases 外の値」= ERROR を新設。SPEC-28/40/50/51 の scheduled を実スプリント（sprint-2）へ設定。phases = [sprint-1, sprint-2, sprint-3] に整理。
- **B（post-mvp 残存）**: post-mvp を phases に残し、scheduled の空許容を維持。scheduled の不統一は許容。

**推奨**: A。理由：`post-mvp` は実スプリントではなく優先度ラベルの概念であり、phases（スプリント計画）と混在することで scheduled の意味論が曖昧になる。実施時期は sprint-N で表現し、post-mvp 扱いは `labels: [post-mvp]` に集約すべき（scheduled と labels の責務分離）。

**決定**: A を採用（オーナー承認・2026-06-14 FND-78 決定B）。

**影響範囲（2026-06-14 即時実施完了）**:
- `docs/doc-system/config.yaml`: `phases` を `[sprint-1, sprint-2, sprint-3]` に変更（post-mvp 除去）。✅ 完了
- `docs/doc-system/05-verification.md`: 段階 0 テーブルに RULE-029 を追加（`scheduled` 値ドメイン検証・非空かつ phases 外 → ERROR）。✅ 完了
- `doc-system/02-what/03-spec.md`: SPEC-28（v0.2→0.3）・SPEC-40（v0.1→0.2）を `scheduled: "sprint-2"` へ変更。SPEC-50（v0.1→0.2）・SPEC-51（v0.1→0.2）を `scheduled: "sprint-2"` へ変更。各ノードに `→FND-78` バックリファレンス付与。✅ 完了
- `doc-system/04-verification/02-findings.md`: FND-78 を `resolved` へ更新。✅ 完了（本 DD 適用で）
- RULE-029 の suppress 可否: `always_error` には含めない（suppress 可能とし、後フェーズ専用 SPEC など合理的理由がある場合は免除を許容）。

---

## DD-10: SPEC-47/NFR-1 の frontmatter 参照を DD-8 準拠に修正

**status: decided**（2026-06-14 反映完了）

<details><summary>⬡ DD-10 · v0.1.0</summary>

```yaml
id: DD-10
type: DD
labels: []
scheduled: ""
suppress: []
edges:
  - to: FND-84
    ref_version: "0.1"
```
</details>

**指摘時 ref_version**: FND-84 "0.1"（findings.md v0.1 時点）

**論点**: FND-84 で指摘（ERROR）。DD-8（2026-06-14 確定）でファイルレベル YAML frontmatter `version:` フィールドは全廃されノードバッジ x.y が版管理の唯一の真実源となった。しかし SPEC-47 は「全 in-graph ファイルの frontmatter に `version` フィールドが存在する」ことを ERROR 要求し（廃止済みの仕組みを要求）、NFR-1 本文は「プレーン Markdown＋YAML フロントマター」と記述しファイルレベルフロントマターの存在を前提としていた。

**選択肢**:
- **A（SPEC-47 内容置換・NFR-1 本文訂正）**: SPEC-47 を「全 in-graph ノードの summary バッジに version（x.y）が存在する」検証へ置換。NFR-1 本文から「YAML フロントマター」の記述を除去し、インライン YAML ブロック埋め込み形式に訂正。
- **B（SPEC-47 廃止）**: SPEC-47 を削除（孤立ノード化するため suppress かラベルで無効化）。NFR-4 のノードバッジ検証は別途 SPEC を著作。
- **C（現状維持）**: DD-8 矛盾を許容し SPEC-47 を凍結する。

**推奨**: A。NFR-4（ファイル単位バージョニング・1 ファイル 1 責務）は DD-8 後もノードバッジでの版管理として有効であり、SPEC-47 はその検証 SPEC として機能する。検証対象を frontmatter → ノードバッジに切り替えることで DD-8 準拠を達成できる。B は検証カバレッジの穴を生む。C は ERROR 違反の放置で不採用。

**決定**: A を採用（オーナー承認・2026-06-14 FND-84 決定）。

**影響範囲（2026-06-14 即時実施完了）**:
- `doc-system/02-what/03-spec.md`: SPEC-47（v0.1→0.2）を「全 in-graph ノードの summary バッジに version（x.y）が存在する」検証内容へ置換。`→FND-84` バックリファレンス付与。✅ 完了
- `doc-system/02-what/02-nfr.md`: NFR-1（v0.3→0.4）本文の「YAML フロントマター」記述を「インライン YAML ブロック（`<details>` 内埋め込み）」に訂正。`→FND-84` バックリファレンス付与。✅ 完了
- `doc-system/02-what/03-spec.md`: SPEC-44（v0.1→0.2）の NFR-1 への `ref_version` を `"0.3"`→`"0.4"` に更新（NFR-1 MINOR バンプに伴うドリフト解消）。✅ 完了
- `doc-system/04-verification/02-findings.md`: FND-84 を `resolved` へ更新。✅ 完了（本 DD 適用で）

---

## DD-11: NFR 由来本文検査の rule-id 体系を `{NFR-id}-check` で正式採用（台帳登録）

**status: decided**

<details><summary>⬡ DD-11 · v0.1.0</summary>

```yaml
id: DD-11
type: DD
labels: []
scheduled: ""
suppress: []
edges:
  - to: FND-86
    ref_version: "0.1"
```
</details>

**指摘時 ref_version**: FND-86 "0.1"（findings.md v0.1 時点）

**論点**: FND-86 で指摘（INFO）。NFR 由来の本文検査（SPEC-44〜49 が検証する NFR-1〜6）の出力行3列目 rule-id が `{NFR-id}-check`（例 `NFR-1-check`）で記載されているが、正準ルール台帳（`docs/doc-system/05-verification.md` の `RULE-NNN`）に登録がなく、全 rule-id を台帳から一覧できない。出力契約（O-1 RULE 違反レポート）における違反 ID の名前空間が二重化しており、消費側（reconciliation・spec-inspector）の解釈がぶれる。

**選択肢**:
- **A（RULE-NNN 採番）**: RULE-030〜035 を新設し、SPEC-44〜49 の出力例6件を `{NFR-id}-check` → `RULE-NNN` へ差し替える。
- **B（`{NFR-id}-check` 正式採用）**: `{NFR-id}-check` を NFR 由来検査の正式 rule-id 体系として台帳に1家族（NFR-1〜6 各1検査）として登録。SPEC 例は据置。
- **C（現状維持）**: 台帳未登録のままとする。

**推奨**: B。理由: (1) DD-5 が NFR→SPEC 導出で「番号付き RULE は新設せず config 駆動」を既に採用済みで、`{NFR-id}-check` 据置はこの方針と整合。(2) `NFR-1-check` は対応 NFR へ直接トレース可能（`RULE-030` は不透明）。(3) SPEC 例の churn ゼロ。C は台帳の網羅性穴を残すため不採用。

**決定**: B を採用（暫定・設計フェーズ）。`docs/doc-system/05-verification.md` の RULE 台帳に「NFR 由来本文検査: rule-id = `{NFR-id}-check`（NFR-1〜6 各1検査・SPEC-44〜49）」を1家族として登録する。

**影響範囲**:
- `docs/doc-system/05-verification.md`（out-of-graph）に台帳行を追加（reconciliation 反映後に主文脈で実施）。
- SPEC-44〜49 の出力例は変更なし。
- `doc-system/04-verification/02-findings.md`: FND-86 を `resolved` へ更新。
- **覆る場合**: 将来 A（RULE-NNN 採番）へ切替えるなら SPEC-44〜49 の出力例6件＋台帳行＋関連 TC を一括改修（影響は spec 層6ノードの 例 と台帳に限定）。

---

## DD-12: 分析層 DFD レベリング深化＋スタンプ結合排除の全面改訂

**status: decided**（2026-06-15 設計確定・本ファイル反映は reconciliation が実施）

<details><summary>⬡ DD-12 · v0.1.0</summary>

```yaml
id: DD-12
type: DD
labels: []
scheduled: ""
suppress: []
edges:
  - to: FND-93
    ref_version: "0.1"
```
</details>

**指摘時 ref_version**: FND-93 "0.1"（findings.md・本バッチ起票時点）

**論点**: オーナー指摘 3 点（①D-3 はスタンプ結合のため分割必須、②D-4・I-1 系など同種スタンプ結合の洗い出しと分割、③DFD レベリングが Lv1/Lv2 止まりで単一動詞に達していない）と、設計で裏取りした既存欠陥（D-4 の condition/result/log_ref 欠落＝価値経路の穴＝FND-93）を、分析層をどう改訂して解消するか。とくに (a) 巨大 composite な D-3/D-4 をどう扱うか（退役 vs 概念保持）、(b) 4 検査子に重複埋め込みされた抑制・発火フィルタをどう配置するか、(c) 系外入力を自称する I-1-1/1-2/1-3 をどう是正するか、(d) どこまでプロセスを分解するか。

**選択肢**:
- **A（内部中間生成物化＋分割 D 配布・抑制プロセス新設・I-1-x 退役・リーフ単一動詞分解）**: D-3/D-4 を退役せず「P-5／P-1 の内部中間生成物」として概念保持し、外部配布はフィールド単位／消費スライス単位の分割 D（D-9〜D-22）が担う。抑制・発火フィルタ（P-2-5）を横断関心事として新設し各検査子を「検出」単一責務にする。I-1-1/1-2/1-3 を退役し D-18/D-19 の派生属性へ吸収。全プロセスをリーフ単一動詞まで分解（P-1/P-2/P-3/P-4/P-5/P-6/P-7 を親化し L2/L3 リーフへ）。
- **B（D-3/D-4 完全退役・全消費辺を分割 D へ張替え）**: D-3/D-4 を退役し、全消費プロセスの辺を分割 D へ全面張替えする。スタンプ結合は同様に解消するが、既存辺の大量付け替えが発生し改訂影響が広い。
- **C（現状維持＋部分対応）**: スタンプ結合・レベリング不足を許容し、FND-93（D-4 の穴）のみ最小修正する。オーナー指摘①〜③が未解決のまま残る。

**推奨**: **A**。理由：(1) 内部中間生成物化は既存辺の大量張替え（B のコスト）を避けつつ「composite を丸ごと配る」状態を実質解消できる（消費先には射影スライスのみ配る）。(2) 退役せず概念保持は PR8（消さない・フル論理）と整合し、D-3 本文に漏れていた config セクションをフル化する好機でもある。(3) P-2-5 への抑制集約は 4 検査子の重複ロジックを 1 箇所に減らし単一責務化（PR9）。(4) I-1-x 退役は PR1/PR9 違反（系外入力でなく D-4 派生属性）の是正。C は指摘未解決で不採用、B は影響過大で不採用。

**決定（A を採用・オーナー指示「全面的見直し実施」「再開」＝即実行）**:
- **(a) D-3/D-4 を退役せず内部中間生成物化し分割 D（D-9〜D-22）で配布**: D-3 は「P-5 内部の検証済み config map」、D-4 は「P-1 内部の正規化集合」として概念保持。外部配布はフィールド単位 D-9〜D-16（D-3 由来）・消費スライス D-17〜D-22（D-4 由来）が担う。D-3 は漏れていた config セクション（decision_spine/coverage_rules/always_error/condition_vocab）をフル化、D-4 は condition/result/log_ref を内部表現に含む旨を明記（FND-93 解消）。両者 MINOR バンプ。
- **(b) P-2-5（抑制・発火フィルタ）を横断関心事として新設**: suppress/scheduled/activate_stage/always_error の適用が 4 検査子に重複コピーされていたのを 1 プロセスに集約。各検査子は「論理違反候補の検出」単一責務とし、P-2-5 が D-9（フェーズ／ステージ）・D-12（always_error）・D-14（発火ステージ）・D-18（suppress/scheduled スライス）で濾して D-6 を確定する。
- **(c) I-1-1 / I-1-2 / I-1-3 を退役**（系外入力ではなく D-4 派生属性）: suppress→D-18、scheduled→D-18／D-9 突合、ref_version→D-19 へ吸収。退役理由を本文に残し（PR8）、退役 ID は再利用しない（DD-7）。
- **(d) 全プロセスをリーフ単一動詞まで分解**: P-1（→P-1-1〜6）・P-2（→P-2-1〜4 の L3 リーフ＋P-2-5）・P-3（→P-3-1〜2 の L3 リーフ）・P-4（→P-4-1〜4）・P-5（→P-5-1〜3）・P-6（→P-6-1〜2）・P-7（→P-7-1-x／P-7-2-x）を親化。階層スキップ（PR9）を排除し、外部・データストア・分割 D は L1/L2 境界で受けて親経由で子へ分配。

**影響範囲**（本ファイル反映は別パス＝analysis-author→reconciliation。本 DD は分析層の全面改訂を伴うため大規模）:
- `doc-system/03-analysis/02-io.md`（**大改訂**）: 新規 D-9〜D-22 起票（D-15/D-22 は post-mvp）。D-3 改訂（外部配布を D-9〜D-16 に移譲・config セクションフル化・消費先列を「P-5 内部のみ」へ・MINOR）。D-4 改訂（外部配布を D-17〜D-22 に移譲・condition/result/log_ref を内部表現に含む明記・消費先列を「P-1 内部のみ」へ・MINOR・FND-93 backref）。I-1-1/I-1-2/I-1-3 退役（退役理由を本文に残す）。
- `doc-system/03-analysis/03-processes.md`（**大改訂**）: P-5/P-6/P-1/P-2/P-2-1〜4/P-3-1〜2/P-4/P-7-1/P-7-2 を親化、子リーフ（P-5-1〜3・P-6-1〜2・P-1-1〜6・P-2-1-1/1-2・P-2-2-1〜4・P-2-3-1〜4・P-2-4-1〜3・P-2-5・P-3-1-1〜3・P-3-2-1/2・P-4-1〜4・P-7-1-1〜3・P-7-2-1/2）を新規著作。P-8/P-9 の入力を D-22（＋P-9 は D-15）へ。各改訂ノードに `→DD-12` バックリファレンス付与。
- `doc-system/03-analysis/00-dfd.md`（**全面差替**）: 新 L0/L1/L2/L3 へ差替（派生図・out-of-graph・ノード版追従で再生成）。
- 各リーフ P→SPEC は既存の最も具体的な SPEC へ暫定マップ（新規 SPEC は作らない）。1:1 対応の無いリーフは Q-2 で要件層波及をオーナー判断に委ねる。
- **覆る場合の影響範囲**: 分割 D の粒度・P-2-5 の責務配置を見直す場合、io.md の D-9〜D-22 定義と processes.md の検査子⇔D 配線、00-dfd.md の L1/L2/L3 を一括改修する（分析層 3 ファイルに限定・要件層 SPEC は Q-2 の決定次第で波及）。

---

## DD-13: MOD 粒度の選択

**status: decided**（2026-06-16 暫定決定／2026-06-17 改訂・設計フェーズ）

> **改訂理由（MINOR バンプ v0.2→v0.3）**: FND-98（ダッシュボード・PR 本文の DD-13 v0.2 陳腐化）の解消に伴い `→FND-98`（ref_version "0.1"）バックリファレンス辺を付与（2026-06-20）。
> **改訂理由（MINOR バンプ v0.1→v0.2）**: 判断基準を「L1 単位 + P-2-5 例外」から「孫プロセスあり OR 責務が明確に別 → L2 分割」に変更（2026-06-17）

<details><summary>⬡ DD-13 · v0.3.0</summary>

```yaml
id: DD-13
type: DD
labels: []
scheduled: ""
suppress: []
edges:
  - to: FND-98
    ref_version: "0.1"
```
</details>

**論点**: spec-inspector の Python モジュール粒度をどの DFD レベルに合わせるか。「L2/L3 リーフ単位（1プロセス1モジュール）」「L1 親プロセス単位（1親P1モジュール）」のいずれにするか。ただし横断関心事の集約（P-2-5）など単一責務が明確なものをどう扱うか。

**選択肢**:
- **A: L2/L3 リーフ全単位**（34+ モジュール）。例: P-1-1: file_reader.py, P-1-2: marker_scanner.py … 各リーフ 1:1 でモジュール化。
- **B: L1 親プロセス単位**（+ P-2-5 例外）。例: P-1 全体を parser.py に集約。P-2-5 のみ横断責務のため独立 filter.py とする。← **旧決定（v0.1）**
- **C: 中間粒度（判断基準ベース）**「孫プロセス（L3 以深）あり OR 責務が明確に別 → L2 単位で分割。孫なし＋同一責務圏 → L1 維持」。← **新決定（v0.2）**

**推奨**: **C**。A より少なく B より細かい中間粒度。リーフ全 1:1（A）はモジュールが爆発して管理不能だが、L1 一括（B）は L2 が複数 L3 を抱える親プロセスで 1 モジュール内の関数数が爆発し、責務が異なる処理が同居してしまう。孫の有無と責務圏を判断基準に据えることで、両極の弊害を回避する。

**決定**: **C を採用**（オーナー要確認で覆る場合は影響範囲参照・2026-06-17 改訂）。

**根拠**:
- 旧決定 B（L1 単位）は、P-2 / P-3 / P-7 の各 L2 がそれぞれ 2〜4 本の L3 リーフを持つことが分析で判明し、1 モジュール内の関数数が爆発する（例: P-2 配下に P-2-1〜P-2-4 の各 L3 を含めると checker.py 単体に十数関数が集中）。L2 単位に割ることで各モジュールの責務と関数数が適正化される。
- P-1-6（検査ビュー射影）は孫を持たないが、「D-4 → 消費スライス D-17〜D-21 への射影」というビュー工場責務であり、parser.py の read→scan→parse→validate→assemble 変換パイプラインとは責務が明確に異なるため分離対象（孫なしでも責務が別なら分割の典型例）。
- P-1-1〜P-1-5 は read→scan→parse→validate→assemble の密結合直列パイプラインで同一責務圏のため L1 単位（parser.py）に維持する。
- P-4 / P-5 / P-6 は L2 のみ・孫なし・同一責務圏のため L1 単位（reporter.py / config.py / collector.py）を維持する。
- 旧 B の P-2-5 例外（横断関心事を独立モジュール filter.py に）は新基準「責務が明確に別 → 分割」に自然に包含される（特例扱いをやめ一般則で説明できる）。

**影響範囲**（本ファイル反映は別パス＝design-author→reconciliation。本 DD 改訂に伴う MOD 改訂で反映辺は reconciliation 時に X→DD-13 を付与）:

更新対象（既存 MOD の MINOR バンプ）:
- **MOD-4**（parser.py → P-1）: 責務を P-1-1〜P-1-5（変換パイプライン）に限定。P-1-6 は MOD-13（projector.py）へ分離。MINOR バンプ v0.1→v0.2。
- **MOD-5**（checker.py → P-2）: drift_checker.py へ改名・参照先を P-2-1 へ変更。MINOR バンプ v0.1→v0.2。
- **MOD-7**（coverage.py → P-3）: graph_coverage.py へ改名・参照先を P-3-1 へ変更。MINOR バンプ v0.1→v0.2。
- **MOD-9**（author.py → P-7）: 参照先を P-7-1（著作側）へ変更。MINOR バンプ v0.1→v0.2。

新規追加 MOD（6 件）:
- **MOD-13**: projector.py（→ P-1-6・検査ビュー射影／ビュー工場責務）
- **MOD-14**: structure_checker.py（→ P-2-2）
- **MOD-15**: condition_checker.py（→ P-2-3）
- **MOD-16**: verification_checker.py（→ P-2-4）
- **MOD-17**: spec_coverage.py（→ P-3-2）
- **MOD-18**: reconciler.py（→ P-7-2・調停側）

維持（変更なし）:
- filter.py（→ P-2-5・横断関心事の抑制/発火フィルタ）、reporter.py（→ P-4）、config.py（→ P-5）、collector.py（→ P-6）は L1/単一責務単位を維持。

総 MOD 数: 12 → 18。

**覆る場合の影響範囲**: 判断基準を A（リーフ全単位）または B（L1 一括）へ戻す場合、MOD-4/5/7/9 の参照先と MOD-13〜18 の新設/削除、依存規則図（core レイヤのモジュール列）を一括改修する（影響は設計層 module-architecture とクラス設計に限定・分析層 P ノードは不変）。

## DD-14: FileSystemPort の抽象化粒度

**status: decided**（2026-06-16 暫定決定・設計フェーズ）

<details><summary>⬡ DD-14 · v0.1.0</summary>

```yaml
id: DD-14
type: DD
labels: []
scheduled: ""
edges: []
```
</details>

**論点**: ファイルシステムアクセスを抽象化するポートを「list_md_files + read_file を1つにまとめる FileSystemPort」にするか「ListPort / ReadPort を別々に定義」するか。

**選択肢**:
- A: 単一 FileSystemPort（list_md_files: Path → list[Path], read_file: Path → str）
- B: ListFilesPort と ReadFilePort を別ポートとして定義

**推奨**: A（単一 Port）。理由: list と read は常にペアで使われ（list してから各ファイルを read）、別 Port にしても合成ルートの DI が複雑になるだけで利点がない。FakeFsAdapter も1つ実装すれば済む。Python の `Protocol` で2つのメソッドを持てばよい。

**決定**: A を暫定採用（2026-06-16）

**影響範囲**:
- PORT-1（FileSystemPort）は2メソッド持つ単一 Protocol として定義
- MOD-11（adapters/fs.py）は RealFsAdapter + FakeFsAdapter の2クラスを同一ファイルに置く
- 将来 write_file が必要になった場合は FileSystemPort にメソッドを追加（MINOR バンプ）するか、WritePort を別途追加する

---

## DD-15: ORC の must_link_to 参照先を P から E へ変更（設計ノードの上流参照の定義）

**status: decided**（2026-06-18 設計フェーズ）

<details><summary>⬡ DD-15 · v0.1.0</summary>

```yaml
id: DD-15
type: DD
labels: []
scheduled: ""
suppress: []
edges: []
```
</details>

**論点**: ORC（オーケストレーション）の `must_link_to` の参照先を P（プロセス）にするか E（イベント）にするか。設計ノードの上流参照をどう定義するかの問題。現行 config.yaml では `must_link_to: ORC → [P]`（「ORC はプロセスを実装」・MOD→P と同型）だが、ORC の識別子の本質は「何がパイプラインを起動するか」であり、MOD→P が捉える「モジュールがプロセスを実装」とは別の依存関係を表すべきではないか。

**選択肢**:
- **A（ORC→P）**: 「ORC はプロセスを実装」。設計→分析トレーサビリティを確保し、MOD→P と同型の参照とする。
- **B（ORC→E）**: 「ORC は起動イベントを参照」。ORC の識別子は "何がパイプラインを起動するか" であり、MOD→P とは別の依存関係（トリガ依存）を捉える。

**推奨**: **B**。

**根拠**:
- ORC の本質は「何をトリガに・どの順序でプロセスを走らせるか」の記述である。トリガ（E）への参照こそが必須であり、P への参照（実行段の列挙）は本文で表現できる。
- MOD→P で「モジュールがプロセスを実装」する関係は既にカバーされており、ORC→P は同じ軸の重複になる。
- ORC→E がなければ "何が起動するか" が RULE で保証されず、ORC が浮いた設計（トリガ未定義）になりえる。

**決定**: **B を採用**（2026-06-18）。`must_link_to: ORC → [E]` に変更し、ORC は起動イベントへの参照を必須とする。

**影響範囲**（本ファイル反映は別パス＝design-author→reconciliation。反映辺は reconciliation 時に X→DD-15 を付与）:
- `docs/doc-system/config.yaml`（out-of-graph）: `must_link_to` の ORC target を `P` → `E` に変更（reason を「ORC は起動イベントを参照する」に更新）。`must_be_linked_from` に `E ← [ORC]`（design ステージ・warning・「イベントは起動する ORC を持ちうる」）を追加。
- `doc-system/05-design/03-orchestration.md`: ORC-1 に `→E-1` 辺を追加（MINOR バンプ v0.1→v0.2）。`→DD-15` バックリファレンス付与。従来の P への参照は本文で実行段として表現する。
- `.claude/skills/architecture-design/SKILL.md`（out-of-graph）: `must_link_to` 表に `ORC → E(trigger)` を追記し、ORC→P が重複である旨を注記。

**覆る場合の影響範囲**: A（ORC→P）へ戻す場合、ORC-1 の E-1 辺を削除し P 辺を必須に戻す、config.yaml の `must_link_to` ORC target を E→P に戻し `must_be_linked_from: E←[ORC]` を撤回、SKILL.md の表を元に戻す（影響は設計層 orchestration と config・SKILL に限定・分析層 E ノードは不変）。

---

## DD-16: FND 専用ライフサイクルルールを config に独立定義（Q-4 から昇格・辺逆転の正式化）

**status: decided**（2026-06-21 オーナー承認・選択肢A 採用）

<details><summary>⬡ DD-16 · v0.1.0</summary>

```yaml
id: DD-16
type: DD
labels: []
scheduled: ""
suppress: []
edges: []
```
</details>

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

---

## DD-17: config 駆動の「禁止接続/辺残留」検出に専用 RULE-030 を新設（欠如 RULE-006 と残存 RULE-030 を責務分離）

**status: decided**（2026-06-22 オーナー承認・案B 採用）

<details><summary>⬡ DD-17 · v0.1.0</summary>

```yaml
id: DD-17
type: DD
labels: []
scheduled: ""
suppress: []
edges: []
```
</details>

> **辺の扱い**: 本 DD は decided。本決定の反映先は主に out-of-graph（`docs/doc-system/05-verification.md` の RULE 表・`docs/doc-system/config.yaml` の `fnd_lifecycle.resolved.must_not_link_to`）であり、in-graph の義務辺（DD→X）は反映済みのため張らない（DD-16 の `edges: []` と同方針）。本決定で resolved 化される FND-104 が in-graph の代表処置対象であり、処置側（FND-104）から `→DD-17` のバックリファレンス辺を張り返す（FND-104 v0.2 で付与・X→DD 慣行）。dedicated SPEC（SPEC-59）は RULE-030 を引くが、SPEC が RULE/DD への辺を張る慣行はないため `SPEC-59→DD-17` は不要。したがって本 DD の `edges: []`。先例: DD-9（RULE-029 新設・`→FND-78` 1 辺）・DD-16（`edges: []`・out-of-graph 反映＋処置側張り返し）。
> **指摘時 ref_version の記録（DD-3 制度）**: 本 DD は FND-104 の指摘を受けて決定したものだが、DD であり FND でないため「指摘時 ref_version」の本文記録は不要（DD-16 と同扱い）。論点の出所は FND-104（findings.md v0.1 時点）である旨を論点欄に記す。

**論点**（FND-104 より昇格）: main の Q-4→DD-16 で `config.yaml` に正式化された `fnd_lifecycle.resolved.must_not_link_to`（target: any・severity warning・「resolved FND の元 forward 辺は削除済みであること」＝辺残留/禁止接続の存在の検出）に対し、それを検出・報告する RULE 番号が `docs/doc-system/05-verification.md` の RULE 一覧に存在しない（検出機構の定義そのものの空白）。既存 RULE は意味が合致しない:

- RULE-006（段階②・必須接続の**欠如**）は `must_link_to`/`must_be_linked_from` のみを対象とし、`must_not_link_to`（辺が**残ってはならない**）とは意味が逆。
- RULE-001/002/022（段階①・義務辺**残存**）は DD/Q/PEND の `decision_spine` **ノード型固有**ルールであり、config 駆動の汎用「辺残留」ルールではない。

結果として「config 駆動・任意型・辺が残留してはならない」検出を引ける RULE コードが空白で、検証ツール実装時に `must_not_link_to` 違反をどの RULE で報告するか決められず、FND-103 ②案の dedicated SPEC（resolved 系）も参照すべき RULE 番号を引けない。

**選択肢**:
- **案A（RULE-006 拡張）**: 既存 RULE-006 の定義を拡張し、config 駆動の `must_not_link_to`（辺残留・禁止接続の存在）も RULE-006 で報告する。RULE 番号を増やさず済むが、RULE-006 が「必須接続の欠如」と「禁止接続の残存」の**2責務**を持ち単一責務が緩む（欠如と残存は検出ロジックも逆・severity も error/warning で異なる）。
- **案B（新規 RULE-030 新設・推奨）**: 「config 駆動の禁止接続/辺残留の存在」を独立 RULE-030 として新設し、欠如（RULE-006）と残存（RULE-030）を責務分離する。RULE-001/022 が義務辺の残存を独立 RULE にしている先例と整合し、FND-103 ②案の dedicated SPEC（SPEC-59）はこの RULE-030 を引く。

**推奨**: 案B。理由: (1) RULE-006 の単一責務を守る（PR1「もの＋発生源で分ける」＝欠如と残存は検出ロジックも severity も別もの）。(2) RULE-001/022 が義務辺の残存を独立 RULE にしている既存先例と一貫する。(3) FND-103 の配置決定（辺欠如 vs 辺残留を別 SPEC に責務分離）と層が揃う。案A は RULE-006 を 2 責務化し、欠如（error）と残存（warning）という意味も severity も逆のロジックを 1 RULE に押し込むため非推奨。

**決定**: **案B を採用**（オーナー承認・2026-06-22）。RULE-030 を `docs/doc-system/05-verification.md` 段階①に新設し、config 駆動の禁止接続/辺残留（`fnd_lifecycle.resolved.must_not_link_to` を含む汎用の `must_not_link_to`）の存在を WARNING で報告する。FND-103 ②案で新設する dedicated SPEC（SPEC-59）は RULE-030 を引く。

**影響範囲（2026-06-22 反映状況）**:

機械判定の正本:
- `docs/doc-system/config.yaml`（out-of-graph）: **変更不要**。`fnd_lifecycle.resolved.must_not_link_to` 自体は DD-16 で既にコミット済み。RULE 番号（RULE-030）は config 側に持たず 05-verification.md 側でマップする（RULE-006 と同方式＝config が機構、05-verification.md が RULE 番号台帳）。✅ 変更なし

out-of-graph RULE 台帳:
- `docs/doc-system/05-verification.md`: 段階①に RULE-030（config 駆動の禁止接続/辺残留の存在＝`must_not_link_to` 違反・任意型・WARNING）を新設。本文注記で RULE-001/022（decision_spine のノード型固有残存）および RULE-006（必須接続の欠如・段階②）との責務分離を明記。✅ 反映済み（本セッション既了）

in-graph ノード（別ファイル差分で出力）:
- `doc-system/02-what/03-spec.md`: SPEC-59（fnd_lifecycle resolved 系 `must_not_link_to` の dedicated SPEC）の期待動作・例の参照 RULE を RULE-006→RULE-030 に差し替え、`→FND-103`・`→FND-104` バックリファレンスを付与（→ `tmp/sprint-1/SPEC-59.md`・reconciliation 反映）。
- `doc-system/04-verification/02-findings.md`: FND-104（v0.1→0.2）を resolved 化（→ `tmp/sprint-1/FND-104.md`）。処置側から本 DD へ `FND-104→DD-17` を張り返す。FND-103（v0.1→0.2）も ②案完了で resolved 化（→ `tmp/sprint-1/FND-103.md`）。

**接続規則変更チェック（FND-99 パターン）**: 本 DD は **05-verification.md の RULE 台帳に RULE-030 を追加するのみ**で、`config.yaml` の接続規則（`must_link_to`/`must_be_linked_from`/`fnd_lifecycle` の `must_not_link_to`）の追加・変更・削除を**含まない**（`fnd_lifecycle.resolved.must_not_link_to` 規則自体は DD-16 で既にコミット済み・本 DD はその検出 RULE 番号を台帳に充てるのみ）。よって接続マトリクス・ドキュメント一覧・各 author エージェント／スキルへの規則伝播は**不要**。ただし RULE 台帳に番号が増えた事実（RULE 範囲 001〜030）は dashboard 参考の RULE 範囲記述に反映する（番号台帳の更新であって接続規則の変更ではない）。

**覆る場合の影響範囲**: RULE-030 を撤去し、SPEC-59 の参照 RULE を差し替える（案A へ回帰するなら RULE-006 拡張＋SPEC-59 を RULE-006 参照へ戻す）。

---

## DD-18: `resolved` の boolean 型検証（SPEC-60-3）に専用 RULE-031 を新設（共通必須型 RULE-028 と型別任意型 RULE-031 を責務分離）

**status: decided**（2026-06-23 オーナー指摘「型検証を SPEC-60-3 として対象化」を受けた設計判断・案B 採用）

<details><summary>⬡ DD-18 · v0.1.0</summary>

```yaml
id: DD-18
type: DD
labels: []
scheduled: ""
suppress: []
edges: []
```
</details>

> **辺の扱い**: 本 DD は decided。本決定の反映先は主に out-of-graph（`docs/doc-system/05-verification.md` 段階0 の RULE 表に RULE-031 を追加）であり、in-graph の義務辺（DD→X）は反映済みのため張らない（DD-16/17 の `edges: []` と同方針）。本決定の in-graph 代表処置対象は FND-105（resolved・スコープ外撤回）であり、処置側（FND-105）から `→DD-18` のバックリファレンス辺を張り返す（FND-105 v0.2 で付与・X→DD 慣行）。dedicated SPEC（SPEC-60-3）は RULE-031 を引くが、SPEC が RULE/DD への辺を張る慣行はないため `SPEC-60-3→DD-18` は不要。したがって本 DD の `edges: []`。先例: DD-17（RULE-030 新設・`edges: []`・out-of-graph 反映＋処置側 FND-104 から張り返し）・DD-16（`edges: []`）。
> **指摘時 ref_version の記録（DD-3 制度）**: 本 DD は FND-105 のスコープ外撤回に伴い決定したものだが、DD であり FND でないため「指摘時 ref_version」の本文記録は不要（DD-16/17 と同扱い）。論点の出所は FND-105（findings.md v0.1 時点・当初「②案＝別軸」としてスコープ外化していた論点）である旨を論点欄に記す。

**論点**（FND-105 の②案より昇格）: `resolved` フィールドの入力空間を SPEC-60-1（`true`→resolved）／SPEC-60-2（boolean `false`・キー未設定→unresolved）／SPEC-60-3（boolean でない型不正）の3子 SPEC で完全分割するにあたり、SPEC-60-3 が要求する「`resolved` フィールドが存在するが boolean でない（文字列 `"true"`・数値 `1`・null 等）」の検出・報告をどの RULE で行うかが空白だった。FND-105 当初は型検証を「②案＝判定セマンティクス規定（①案）とは別軸」としてスコープ外に追い出していたが、オーナー指摘により撤回し SPEC-60-3 として SPEC-60 傘の対象に組み込む方針に変更した。既存 RULE は意味が合致しない:

- RULE-028（段階0・共通必須フィールドの存在と型）は `labels`/`scheduled`/`edges` 等の**全ノード共通必須フィールド**を fail-close で検証する。一方 `resolved` は **FND 固有の任意フィールド**であり、共通必須でも全ノード対象でもない。RULE-028 で拾うと「共通必須」と「FND 固有任意」の2責務を1 RULE が抱える。
- 非 boolean を黙って `false` 既定に解決すると（現行 SPEC-60-2 文言「`true` でないとき」は非 boolean まで拾う）、型不正の握り潰しになる。検出と報告を担う RULE が必要。

**選択肢**:
- **案A（RULE-028 拡張）**: 既存 RULE-028（共通必須フィールドの型検証）を拡張し、FND 固有の任意フィールド `resolved` の boolean 型検証も RULE-028 で行う。RULE 番号を増やさず済むが、(1) RULE-028 が「共通必須フィールドの型」＋「型別（FND 固有）任意フィールドの型」の**2責務**を持ち単一責務が緩む。(2) `resolved` は**任意**フィールドであり、RULE-028 の fail-close（必須欠如はノード単位で打ち切り）方針とも整合しない（任意フィールドの型不正は fail-close すべき性質ではない）。
- **案B（新規 RULE-031 新設・推奨）**: 「型別（FND 固有）任意フィールドの型検証」を独立 RULE-031 として新設し、共通必須フィールド型（RULE-028）と型別任意フィールド型（RULE-031）を責務分離する。`condition`→RULE-016・`result`→RULE-020 の既存「型別フィールドは専用 RULE」パターンと整合する。

**推奨**: 案B。理由: (1) RULE-028 の単一責務を守る（PR1「もの＋発生源で分ける」＝共通必須フィールドの型と型別任意フィールドの型は対象も発火条件も別もの）。(2) `condition`（FND/SPEC 等の型別フィールド）→RULE-016、`result`（TR の型別フィールド）→RULE-020 と同じく「型別フィールドは専用 RULE で検証する」既存パターンに揃う。(3) `resolved` は任意フィールドで非 fail-close（型不正でもノード処理を打ち切らず ERROR 報告のみ）にできるため、fail-close 前提の RULE-028 とロジックが異なる。案A は RULE-028 を 2 責務化し、必須/fail-close と任意/非 fail-close という性質の異なる検証を1 RULE に押し込むため非推奨。

**決定**: **案B を採用**（主文脈・2026-06-23）。オーナー指摘「型検証を SPEC-60-3 として対象化」を受け、RULE-031 を `docs/doc-system/05-verification.md` 段階0（スキーマ検証・RULE-023〜029 の節）に新設する。定義は「型が FND のノード YAML に `resolved` が存在するが boolean でない（型不正）」・深刻度 **ERROR**・**非 fail-close**。RULE-031 発火時は当該ノードの resolved 判定（SPEC-60-1/60-2）を適用せず型不正を報告する（非 boolean を黙って `false` 既定に解決しない）。SPEC-60-3 はこの RULE-031 を引く。なお RULE-028 拡張（案A）vs 新 RULE 新設（案B）の選択はオーナー override 可として本 DD に記録する。

**影響範囲（2026-06-23 反映状況）**:

機械判定の正本:
- `docs/doc-system/config.yaml`（out-of-graph）: **変更不要**。`fnd_lifecycle.resolved_field: resolved` は既コミット済みで、RULE 番号（RULE-031）は config 側に持たず 05-verification.md 側でマップする（RULE-006/030 と同方式＝config が機構、05-verification.md が RULE 番号台帳）。✅ 変更なし

out-of-graph RULE 台帳:
- `docs/doc-system/05-verification.md`: 段階0（スキーマ検証・RULE-023〜029 の節）に RULE-031（型が FND のノードに `resolved` が存在するが boolean でない＝型不正・ERROR・非 fail-close）を追加。本文注記で RULE-028（共通必須フィールドの型）との責務分離、および `condition`→RULE-016・`result`→RULE-020 の「型別フィールドは専用 RULE」パターンとの整合を明記。✅ 反映済み（主文脈で追加済み）

in-graph ノード（別ファイル差分で出力）:
- `doc-system/02-what/03-spec.md`: SPEC-60 傘の対象に SPEC-60-3（failure・`resolved` 型不正→RULE-031 ERROR）を追加、SPEC-60-2 の文言を「boolean の `false`／キー未設定」に限定修正（非 boolean を 60-3 の責務へ切り出し）。SPEC-60-1 は変更なし。SPEC-60 傘本文の「スコープ外」段落を 3 分割の説明へ書き換え（spec-author 所掌）。
- `doc-system/04-verification/02-findings.md`: FND-105（v0.1→0.2）の「スコープ外（明示）」「②案（別軸）」記述を撤回・書き換え（→ `tmp/sprint-1/FND-105.md`）。処置側から本 DD へ `FND-105→DD-18` を張り返す。

**接続規則変更チェック（FND-99 パターン）**: 本 DD は **05-verification.md の RULE 台帳に RULE-031 を追加するのみ**で、`config.yaml` の接続規則（`must_link_to`/`must_be_linked_from`/`fnd_lifecycle` の `must_not_link_to`/`resolved_field`）の追加・変更・削除を**含まない**（`resolved_field: resolved` 定義および省略時 false 既定の規約自体は main の Q-4→DD-16 で既にコミット済み・本 DD はその型妥当性検出 RULE 番号を台帳に充てるのみ）。よって接続マトリクス（`docs/doc-system/03-connection-matrix.md`）・ドキュメント一覧（`docs/doc-system/01-document-items.md`）・各 author エージェント／スキルへの規則伝播は**不要**（接続規則ではなく RULE 番号台帳の追加であり、DD-17 の RULE-030 新設と同じ判定）。ただし RULE 台帳に番号が増えた事実（RULE 範囲 001〜031）は dashboard 参考の RULE 範囲記述に反映する（番号台帳の更新であって接続規則の変更ではない）。

**覆る場合の影響範囲**: RULE-031 を撤去し、SPEC-60-3 の参照 RULE を差し替える（案A へ回帰するなら RULE-028 を拡張し、SPEC-60-3 を RULE-028 参照へ戻す）。SPEC-60-2 の文言限定修正（「boolean の `false`／キー未設定」）も巻き戻し、非 boolean を `false` 既定へ吸収する旧モデルへ戻す。

---

## DD-19: 検証戦略の段階別トリガを §1 フロー図 L13-23 の単一トリガに統一（bump 非依存の辺残留検査のすり抜けを解消）

**status: decided**（2026-06-23 オーナー決定・PR #37 スレッド3・案A 採用）

<details><summary>⬡ DD-19 · v0.1.0</summary>

```yaml
id: DD-19
type: DD
labels: []
scheduled: ""
suppress: []
edges: []
```
</details>

> **辺の扱い**: 本 DD は decided。本決定の反映先は全面的に out-of-graph（`docs/doc-system/05-verification.md` §2 統一トリガ注記の追加・段階①②③′トリガ行の書換）であり、in-graph の義務辺（DD→X）は反映済みのため張らない（DD-16/17/18 の `edges: []` と同方針）。本決定の in-graph 代表処置対象は FND-106（resolved）であり、処置側（FND-106）から `→DD-19` のバックリファレンス辺を張り返す（FND-106 v0.2 で付与・X→DD 慣行）。被指摘の検証戦略文書（05-verification.md）は out-of-graph でノード ID を持たず、DD→文書行の辺は張れない。したがって本 DD の `edges: []`。先例: DD-18（RULE-031 新設・`edges: []`・out-of-graph 反映＋処置側 FND-105 から張り返し）・DD-17（RULE-030 新設・`edges: []`・処置側 FND-104 から張り返し）・DD-16（`edges: []`）。
> **指摘時 ref_version の記録（DD-3 制度）**: 本 DD は FND-106 のトリガ不整合指摘を受けて決定したものだが、DD であり FND でないため「指摘時 ref_version」の本文記録は不要（DD-16/17/18 と同扱い）。論点の出所は FND-106（findings.md v0.1 時点・PR #37 スレッド3 起源・「段階別トリガ宣言がフロー図の単一トリガモデルと不整合」）である旨を論点欄に記す。

**論点**（FND-106 より昇格）: `docs/doc-system/05-verification.md` の §1 フロー図（L13-23）は「ドキュメント変更があったら①②③（④は実装着手後）を順に流す」という**単一トリガモデル**を正本として示している。一方、各段階の `**トリガ**`/`**運用**` 行は段階ごとに別トリガを後付け宣言しており、両者が不整合である。とりわけ段階①トリガ（L44・「ノードのバッジ `vX.Y` を上げたとき」＝bump トリガ）は、段階①に同居する RULE のうち RULE-004（ref_version ドリフト・bump 依存）には妥当だが、RULE-030（禁止接続/辺残留）・RULE-001/002/022（DD/Q/PEND 義務辺残存）は**バッジ bump に依存しない辺残留検査**である。これらを bump トリガに括ると、**バッジ bump を伴わない辺改変コミット**（resolved FND の元 forward 辺 `FND→X` の消し忘れ・必須辺の削除をバッジ据え置きで行った等）で段階①が回らず、辺残留・義務辺残存・禁止接続残留が**すり抜ける検出漏れ gate** が生じる。対照的に辺の**欠如**を見る RULE-006 は段階②（辺改変トリガ）で正しく回るため、同じ「辺の存在状態を検査する」性質が欠如＝辺改変トリガ・残留＝bump トリガという非対称になっている。このトリガ整合をどう取るかが論点。

**選択肢**:
- **案A（トリガ統一・推奨）**: 段階①〜③（③′含む）の `**トリガ**`/`**運用**` 行を §1 フロー図 L13 の単一トリガ（「ドキュメント変更があったとき①②③を全て実行」）に統一する。段階0 の fail-close 境界（ファイル読み込み時・段階①の前）と段階④ の phase-gate（実装着手後・sub-issue）は性質の異なる起動条件のため現行据え置き。フロー図（正本）と段落トリガが一致し、辺改変コミットで段階①の辺残留検査が bump の有無に依存せず確実に回る。RULE-004（bump 依存）も「ドキュメント変更時に毎回走査」に包含され、bump がなければドリフトも生じないため過検出にならない。
  - 利点: 正本（既に単一トリガのフロー図）に段落トリガを揃えるだけの最小変更で検出漏れ経路が閉じる。PR3「必要な検査は処理時に毎回実行」とも整合（トリガ条件で検査を間引かない）。RULE の段階再配置を伴わないため RULE 表・dashboard 段階別集計への波及がない。
  - 留意: CI 上は全 RULE 毎回実行になるが、グラフ走査は軽量で実装層 0 ノードの現状で問題にならない。
- **案B（RULE 再配置）**: トリガは段階別のまま維持し、bump 非依存の辺残留 RULE（RULE-030/001/002/022）を段階②（辺改変トリガ）へ移すか、段階①トリガに「辺の追加/削除（辺改変）時」も併記する。各段階のトリガを検出事象の発生源に厳密対応させる（bump 起因＝RULE-004 は段階①／辺改変起因＝辺残留 RULE は段階②・PR1 発生源基準）。
  - 利点: トリガと検出対象の発生源が 1:1 対応し、各段階が単一の起動条件を持つ。
  - 留意: RULE の段階再配置は RULE 表・本文注記・dashboard の段階別集計に波及し変更面積が大きい。段階①の「ドリフト検出」括りに辺残留（RULE-030/001/002/022）が含まれてきた経緯（FND-104 で RULE-030 を段階①に新設した配置）と整合を取り直す必要がある。
- **案C（現状維持＋根拠明記）**: 段階別トリガを残し、「bump 非依存の辺残留 RULE も実運用では CI で常時走査するため取りこぼさない」旨を本文に注記して整合を文章で担保する。
  - 留意: 文書上のトリガ宣言（bump トリガ）と実運用（常時走査）が乖離したまま残り、文言どおり実装すると検出が落ちる。検出機構の設計整合という指摘の核心を解消しないため非推奨。

**推奨**: 案A。理由: (1) §1 フロー図（L13-23）が既に単一トリガモデルを正本として示しており、段落 `**トリガ**` 行を後付けで段階別に分割した結果が不整合の原因であるため、正本（フロー図）に段落トリガを揃えるのが筋。(2) 最小変更で検出漏れ経路を閉じられる（RULE の段階再配置を伴わず RULE 表・dashboard 段階別集計に波及しない）。(3) PR3（処理時に毎回検査・トリガ条件で間引かない）と整合する。案B は発生源基準では理屈が通るが RULE 表・dashboard まで波及して変更面積が大きく、現状の最小是正には過剰。案C はトリガ宣言と実運用の乖離を残し検出を gate しうる本質を解消しないため非推奨。段階0 fail-close（構造異常での即時中断）と段階④ phase-gate（フェーズゲート）は単一トリガと性質が異なるため統一対象に含めず現行据え置きが妥当。

**決定**: **案A を採用**（オーナー決定・2026-06-23・PR #37 スレッド3）。§1 フロー図を正本とし、段階①〜③（③′含む）のトリガ宣言を単一トリガ（ドキュメント変更時に①②③を一括全実行・CI 常時実行）へ統一する。これにより bump を伴わない辺改変でも段階①の辺残留検査（RULE-030/001/002/022）と RULE-004 が必ず走り、検出漏れ gate が閉じる。段階0（fail-close 境界・ファイル読み込み時）・段階④（phase-gate・実装着手前は対象なし）のみ固有の実行条件を持つ例外として現行維持する。

**影響範囲（2026-06-23 反映状況）**:

機械判定の正本:
- `docs/doc-system/config.yaml`（out-of-graph）: **変更不要**。本決定はトリガ宣言（どの段階をいつ起動するか）の文言整合であり、`must_link_to`/`must_be_linked_from`/`fnd_lifecycle`/`must_not_link_to` 等の接続規則および RULE 定義そのものには触れない。✅ 変更なし

out-of-graph 検証戦略文書:
- `docs/doc-system/05-verification.md`: 主文脈で反映済み。✅
  - §2 冒頭に「検証トリガ（統一・DD-19・FND-106）」注記を追加（段階①②③（③′含む）は段階別トリガを持たず §1 フロー図どおりドキュメント変更時に①②③を一括全実行〔CI 常時実行〕。bump を伴わない辺改変でも段階①の辺残留検査〔RULE-030/001/002/022〕と RULE-004 が必ず走る。段階0〔fail-close 境界〕・段階④〔phase-gate〕のみ固有の実行条件を持つ例外）。
  - 段階①トリガ（旧「バッジ vX.Y を上げたとき」）→ §2 統一トリガに従う旨へ書換（RULE-004 は bump 時に差分が生じるが走査は毎回実行と明記）。
  - 段階②トリガ（旧「ノードの追加・辺の追加/削除後」）→ §2 統一トリガに従う旨へ書換（運用「CI 常時実行・ERROR でマージブロック推奨」は保持）。
  - 段階③′トリガ（旧「NFR 対象成果物の変更後」）→ §2 統一トリガに従う旨へ書換。
  - 段階0 トリガ（ファイル読み込み時＝段階①の前）・段階④（実装着手前は対象なし）は現状維持。

in-graph ノード:
- `doc-system/04-verification/02-findings.md`: FND-106（v0.1→0.2）を resolved 化し、処置側から本 DD へ `FND-106→DD-19`（ref "0.1"）を張り返す。

**接続規則変更チェック（FND-99 パターン）**: 本 DD は **05-verification.md の段階別トリガ宣言を §1 フロー図の単一トリガに整合させる文言修正のみ**で、`config.yaml` の接続規則（`must_link_to`/`must_be_linked_from`/`fnd_lifecycle` の `must_not_link_to`/`resolved_field` 等）および RULE 定義（RULE-001〜031 の意味・配置）の追加・変更・削除を**含まない**。指摘・処置の対象は「どの段階をいつ起動するか」のトリガ宣言（運用記述）であり、「どの型がどの型に辺を張る/張らない」という接続規則や RULE の意味には一切触れない。

よって接続マトリクス（`docs/doc-system/03-connection-matrix.md`）・ドキュメント一覧（`docs/doc-system/01-document-items.md`）・各 author エージェント／スキルへの規則伝播は**不要**（変更される接続規則型なし＝伝播対象なし）。案A は RULE の段階再配置すら伴わないため RULE 表・dashboard の段階別集計への波及もない（案B を採っていた場合のみ RULE 段階配置の見直しが生じたが、案A 採用により発生しない）。先例: FND-106 本文の同チェック・DD-18 の同チェック（RULE 台帳の操作は接続規則変更でない）と同じ判定。

**覆る場合の影響範囲**: 段階①〜③のトリガ宣言を段階別トリガ（bump トリガ・辺改変トリガ・NFR 成果物変更トリガ）へ戻し、§2 統一トリガ注記を撤去する。その際は案B（辺残留 RULE の段階再配置）か案C（常時走査の文章注記）のいずれかで検出漏れ gate を別途閉じる必要がある（単なる現状回帰は FND-106 の検出漏れ gate を再発させるため不可）。

---

## DD-20: O-1/O-2 の生成元辺を親 P-4 からリーフ P-4-3 へ精緻化（Q-3 から昇格・O 生成元粒度のリーフ基準統一）

**status: decided**（2026-06-24 オーナー承認・選択肢A 採用）

<details><summary>⬡ DD-20 · v0.1.0</summary>

```yaml
id: DD-20
type: DD
labels: []
scheduled: ""
suppress: []
edges: []
```
</details>

> **辺の扱い**: 本 DD は decided。本決定の in-graph 反映先は O-1・O-2 の生成元辺の張替え（`→P-4` → `→P-4-3`）であり、その反映は別パス（analysis-author → reconciliation）で行う。**先例（Q-4→DD-16・DD-15）に倣い本 DD は `edges: []` とし、義務辺 DD→O-1/O-2 は張らない**。理由：(1) 本決定の in-graph 代表処置対象は昇格元 Q-3 であり、Q-3 が処置側から `→DD-20`（昇格辺）を張り返すことで本 DD の被参照辺が確保され RULE-005（完全孤立）は生じない。(2) O-1/O-2 の張替えは反映完了時に各ノードへ `→DD-20`（X→DD・ref_version は DD-20 のバッジ x.y）を付与する慣行で経緯を残す（DD-15 で ORC-1 の反映を別パスとし反映時に `→DD-15` を付与した先例と同型）。義務辺 DD→X（未反映の RULE-001 ERROR シグナル）を一旦張って即削除する二度手間を避け、最新の昇格 DD（DD-15〜DD-19 はいずれも `edges: []`）の慣行に揃える。
> **指摘時 ref_version の記録（DD-3 制度）**: 本 DD は Q-3 から昇格（DD であり FND でない）ため「指摘時 ref_version」の本文記録は不要（DD-16/17/18/19 と同扱い）。論点・現状の出所は Q-3（05-questions.md・指摘時 O-1 "0.2"／O-2 "0.2"）である。

**論点**（Q-3 より昇格・要約）: 分析層の過分割（DD-12）後、**O-1・O-2 の生成元辺が親 P-4 を指したまま**であり、実生成リーフ（P-4-3＝G 番号付与・整形）と、リーフ基準の先例（O-3→P-7-2・O-6→P-4-4）および 00-dfd.md の O フロー表「L2 詳細生成元＝P-4-3」と二重に不整合になっている。O の生成元辺（O→P）の粒度を**リーフへ精緻化するか／親のまま許容するか**。

**現状**（Q-3 で Read 確認済み）:
- O-1（v0.2）の生成元辺＝`→P-4`（ref_version "0.1"）。O-2（v0.2）の生成元辺＝`→P-4`（ref_version "0.1"）。
- リーフ基準の先例は確立済み: **O-3→P-7-2**・**O-6→P-4-4**（いずれも親でなく終端リーフへ生成元辺を張る。O-6 本文に「リーフ先例 O-3→P-7-2 に倣って終端リーフ P-4-4 に張る」と明記）。
- 00-dfd.md「出力（O）」フロー表「L2 詳細生成元」列は **O-1=P-4-3・O-2=P-4-3**（P-4 の L2 分解で O-1/O-2 を生成するのは P-4-3「G 番号付与・整形」）。
- すなわち O-1/O-2 のみが「親 P-4 基準」で取り残され、同じ O 型の O-3/O-6 のリーフ基準・フロー表記載と不整合。

**選択肢**（Q-3 より要約・排他）:
- **選択肢A（O-1/O-2 の `→P-4` を `→P-4-3` へ精緻化・推奨）**: リーフ先例（O-3→P-7-2・O-6→P-4-4）および既存フロー表（L2 詳細生成元＝P-4-3）に統一。最小変更（O-1/O-2 の生成元辺 to を P-4-3 へ・ref_version は P-4-3 の現バッジに一致）で O 型全体の生成元辺粒度がリーフ基準で揃う。02-io.md の O-1/O-2 を MINOR バンプ。
- **選択肢B（親 P-4 のまま据え置き）**: 親境界での生成元表現として許容。O-3/O-6 が既にリーフ基準のため O 型内で粒度が割れたまま残る。一貫させるには O 全体を親基準へ寄せ直す広範改訂（O-3→P-7・O-6→P-4 への差し戻し＋フロー表 L2 列の意味再定義）が別途必要で変更範囲が拡大。非推奨。
- **選択肢C（O 生成元辺の粒度方針を先に DD 化し全 O を一括統一）**: 方針自体を先行決定として全 O に適用。既にリーフ基準（O-3/O-6・フロー表）が事実上の先例として存在するため、A を実施してから事後 DD 化で足り、先行 DD 化は過剰手続き。非推奨。

**推奨**: 選択肢A（Q-3 推奨どおり）。

**決定**: **選択肢A を採用**（オーナー承認・2026-06-24）。O-1・O-2 の生成元辺 `→P-4`（ref_version "0.1"）を `→P-4-3`（ref_version は P-4-3 の現バッジ x.y＝"0.1"）へ精緻化し、O 型の生成元辺粒度をリーフ基準で統一する。

**根拠**:
- O-3→P-7-2・O-6→P-4-4 が既にリーフ基準で確立し O-6 本文がリーフ先例に倣う旨を明記しているため、O-1/O-2 のみ親基準で残すのは整合性の穴（PR6 価値経路・生成元の追跡可能性）。
- 00-dfd.md フロー表が既に O-1/O-2=P-4-3 と記載しており、台帳（02-io.md）を派生図に合わせるのが最小変更。
- B は O 型内の不整合を残すか、解消には逆方向の広範改訂を要し変更範囲が拡大。C は事実上の先例があるため先行 DD 化は過剰手続きで、A 実施後の事後 DD 化（＝本 DD）で足りる。

**接続規則変更チェック（FND-99 パターン）**: 本 DD は **個別ノード O-1/O-2 の生成元辺の to を P-4（親）から P-4-3（リーフ）へ張替えるのみ**で、`config.yaml` の接続規則（`must_link_to: O → P` 等）の追加・変更・削除を**含まない**。O→P の規則自体は不変で、辺先がいずれも P 型である点も不変（粒度＝対象ノードの選び方が変わるだけで規則は同一）。よって接続マトリクス（`docs/doc-system/03-connection-matrix.md`）・ドキュメント一覧（`docs/doc-system/01-document-items.md`）・各 author エージェント／スキルへの規則伝播は**不要**。先例: DD-17/18/19 の同チェック（接続規則そのものに触れない変更は伝播不要）と同じ判定。

**影響範囲（A 採用時・2026-06-24 reconciliation で反映完了）**:

in-graph ノード:
- `doc-system/03-analysis/02-io.md`: O-1（v0.2→0.3・MINOR）・O-2（v0.2→0.3・MINOR）の生成元辺 `→P-4`（ref_version "0.1"）を `→P-4-3`（ref_version "0.1"＝P-4-3 現バッジ v0.1.0 の x.y・RULE-004）へ差し替え。両ノード本文の「生成元」記述を P-4-3 基準に改訂（O-6 に倣い「リーフ先例に倣って終端リーフ P-4-3 に張る」旨を明記）。反映時に O-1・O-2 へ `→DD-20`（ref_version は DD-20 バッジ x.y＝"0.1"）バックリファレンス辺を付与（X→DD 慣行）。✅ 反映済み
- `doc-system/04-verification/05-questions.md`: Q-3 を `status: closed`（DD-20 へ昇格）・`→DD-20`（ref_version "0.1"）付与・MINOR バンプ v0.1→v0.2。✅ 反映済み

out-of-graph（再生成不要）:
- `doc-system/03-analysis/00-dfd.md`: 派生図（out-of-graph）で既に O-1/O-2=P-4-3 と記載済みのため再生成不要。

**覆る場合の影響範囲**: 選択肢B（親 P-4 据え置き）へ戻す場合、O-1/O-2 の生成元辺を `→P-4` に戻し `→DD-20` バックリファレンスを撤去、Q-3 を再 open（または別途整理）する。さらに O 型内の粒度一貫を取るには O-3→P-7・O-6→P-4 への差し戻しとフロー表 L2 列の意味再定義が必要になる（影響は分析層 02-io.md の O 群と 00-dfd.md に限定・要件層 SPEC は不変）。

---
