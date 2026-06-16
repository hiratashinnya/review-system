# 意思決定 — Decision Log

> **型**: DD ／ 義務辺（DD→X）が存在する間は「未反映」で RULE-001 ERROR。反映後は辺を削除し、影響を受けたノード側に X→DD を張る（経緯の永続記録）。
> DD は無名依存辺のみ（`kind`/`status` なし・`to` は単数・`ref_version` 必須）。ライフサイクルは本文の status バッジに記載。
> **影響範囲のバージョン注記**（例：`spec.md v0.3.0→0.3.1`）は**決定時点のスナップショット**（DD-2 凍結記録設計）。現時点のファイル版との差異はドリフトではなく当該 DD 以降の追加変更による自然な版上げを示す（FND-31）。

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

---

## DD-8: ノードバッジをノード固有バージョン（x.y.z）に正式化・ファイルフロントマター version 廃止

**status: decided**（2026-06-14 オーナー判断確定）

<details><summary>⬡ DD-8 · v0.1</summary>

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
```
</details>

**論点**: FND-36 により、ノードバッジ `⬡ FR-1 · v0.3` の `v0.3` が「著作時点のファイル x.y スナップショット」（FND-32 の処置で定義した意味）でも「現在のファイル x.y」でもなく、**ノード固有の改訂回数**を実態として示していることが判明した。FND-32 の処置（notation.md に「バッジ＝ファイル x.y スナップショット」と追記）は実態と乖離した誤定義であり、是正が必要。バッジを正式なノードバージョンとして制度化し、ファイルフロントマターの `version:` を廃止することで、ノード追跡性を一貫した形で高める。

**選択肢**:
- **A（ノード固有リビジョン正式化）**: バッジ＝ノード固有の x.y.z バージョン（MAJOR.MINOR）として正式化。`notation.md` の説明文のみ修正。全ノードのバッジ値はそのまま有効で移行作業なし。実態に合致し修正コスト最小。
- **B（ファイル x.y 統一）**: バッジ＝現在のファイル x.y に一致させるため全ノードのバッジを一括修正。大量修正が発生し、ノード改訂履歴の情報（例: FR-1 が 0.3 まで改訂された事実）が失われる。
- **C（バッジ廃止）**: バッジを廃止し `ref_version` のみを版管理の真実源とする。大規模変更が必要で可視性が低下する。

**推奨**: A ベースで拡張。ノードバージョンをファイルフロントマターから独立させ、各ノード固有の x.y.z 体系に正式化する。ファイルフロントマター `version:` は廃止。B は修正コスト大・ノード改訂履歴の消失を招き不採用。C は可視性低下のため不採用。

**決定: A ベースで拡張**（オーナー・2026-06-14）

1. **バッジのノードバージョン正式化**: `⬡ PREFIX-N · vX.Y` の `X.Y` はノード固有バージョン（MAJOR.MINOR）として正式化する。現在のバッジ値はすべてそのまま有効。
2. **ファイルフロントマター `version:` 廃止**: 各ファイルの `---\nversion: "x.y.z"\n---` フィールドは廃止する（2026-06-14 全ファイルから削除完了）。新規ファイルへの記載は行わない。
3. **`ref_version` 参照先変更**: `ref_version` は従来のファイル x.y ではなく、参照先ノードのノードバージョン x.y を指すものとして意味論を変更する。全辺の移行を 2026-06-14 に実施済み（VERIFY ノードの凍結辺＝`01-doc-verify.md`・DD-2 suppress[RULE-004] を除く）。
4. **バンプルール**:
   - 構造変更（YAML キー追加・型変更・辺の追加/削除/変更）→ MINOR バンプ（x.Y）
   - 内容のみ（本文修正・バックリファレンス辺追加・suppress 追加）→ z バンプ（x.y.Z）
   - 大規模構造変更（ノード分割・統合・型変更）→ MAJOR バンプ（X.y.z）
   - z バンプは伝播不要（依存元ノードの ref_version 更新不要）
5. **本 DD 適用時の制約**: 今回のノードバージョン改訂は z バンプのみ・伝播させない（本 DD 起因の改訂で大規模な ref_version 更新を誘発しない）。ref_version の一括移行（下記）は「ファイル x.y → ノード x.y」の座標系再表現であり、ノードバージョンの改訂ではない（バッジは不変）。

**影響範囲（2026-06-14 即時実施完了・sprint-2 への繰り越しはオーナー指示により撤回）**:
- `docs/doc-system/04-notation.md`（out-of-graph・直接更新）: §1/§2/§5/§8 のバッジ・フロントマター説明をノード固有バージョン（MAJOR.MINOR）に更新。FND-32 の処置（「ファイル x.y スナップショット」定義）を上書き訂正。✅ 完了
- `docs/doc-system/02-meta-schema.md`（out-of-graph）: §1「ファイルバージョニング」を「ノードバージョニング」に書き換え、§7 ドリフト定義・RULE-004 表を「参照先ノードのバッジ x.y」基準に更新。✅ 完了
- `docs/doc-system/05-verification.md`（out-of-graph）: 段階①ドリフト検出・RULE-004 の判定基準を「参照先ノードのバッジ x.y」に更新、トリガを「ノードバッジの版上げ」に変更。✅ 完了
- `docs/doc-system/config.yaml`（out-of-graph）: 冒頭に DD-8 注記（版管理単位＝ノードバッジ・RULE-004 はノード x.y 基準）を追記。✅ 完了
- **全ノードのバッジ値**: 不変（移行作業なし）。✅
- **全辺の `ref_version`**: ファイル x.y → 参照先ノードのバッジ x.y へ一括移行（live 辺 170 件更新・ドリフト 0 を検証）。VERIFY 凍結辺は DD-2 により据え置き。✅ 完了
- **ファイルフロントマター `version:` 削除**: doc-system 配下・docs/doc-system 配下（テンプレート群含む）全ファイルから削除完了。✅ 完了
- **既知の残存事項（履歴保全・PR8）**: 解消済み FND 本文の `**指摘時 ref_version**:` 記録は当時のファイル x.y を凍結記録したものであり、遡及書き換えは provenance を損なうため実施しない（過去の系の下での記録として保持）。新規 FND は DD-3 の様式でノード x.y を記録する。
- ※以下は当初起票時の実施計画（実施済み確認記録）: `doc-system/04-verification/02-findings.md` の FND-36 を `open` → `resolved` に更新し、本 DD（DD-8）を処置記録として明記。FND-32 の処置誤謬（「ファイル x.y スナップショット」定義）が本 DD により是正済みである旨を FND-32 本文に追記。✅ 完了（FND-39 で指摘の旧版残骸行を削除済み）

---

## DD-9: config.yaml phases から post-mvp 除去・RULE-029 新設

**status: decided**（2026-06-14 反映完了）

<details><summary>⬡ DD-9 · v0.1</summary>

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

<details><summary>⬡ DD-10 · v0.1</summary>

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

<details><summary>⬡ DD-11 · v0.1</summary>

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

<details><summary>⬡ DD-12 · v0.1</summary>

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

**status: decided**（2026-06-16 暫定決定・設計フェーズ）

<details><summary>⬡ DD-13 · v0.1</summary>

```yaml
id: DD-13
type: DD
labels: []
scheduled: ""
edges: []
```
</details>

**論点**: spec-inspector の Python モジュール粒度を「DFD L2/L3 リーフ単位（1プロセス1モジュール）」にするか「DFD L1 親プロセス単位（1親P1モジュール）」にするか。ただし P-2-5（抑制・発火フィルタ）は単独責務・横断関心事の集約として L1/L2 混在でも例外的に独立モジュールとする。

**選択肢**:
- A: L2/L3 リーフ単位（例: P-1-1: file_reader.py, P-1-2: marker_scanner.py ...）
- B: L1 親プロセス単位（例: P-1 全体: parser.py に P-1-1〜P-1-6 を集約）。ただし P-2-5 は L2 プロセスだが単一横断責務のため独立 filter.py とする例外あり

**推奨**: B（L1 単位 + P-2-5 例外）。理由: L2/L3 リーフは34以上あり、1:1 で作ると Python モジュールが爆発して管理不能。Python は関数/クラス単位で分担できるため L1 1:1 で十分。P-2-5 は suppress/scheduled/activate_stage の一元管理責務が明確に区別できるため例外とする。

**決定**: B を暫定採用（設計フェーズ・オーナー要確認で覆る場合は影響範囲参照）（2026-06-16）

**影響範囲**:
- MOD-1〜MOD-12 は L1 プロセス単位で定義（MOD-6 のみ P-2-5 に対応する例外）
- 実装時に L2/L3 の各責務を各 MOD 内の関数/クラスで実現
- L2/L3 分解が必要になった場合はモジュール分割（新 MOD-N 追加）で対応

## DD-14: FileSystemPort の抽象化粒度

**status: decided**（2026-06-16 暫定決定・設計フェーズ）

<details><summary>⬡ DD-14 · v0.1</summary>

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
