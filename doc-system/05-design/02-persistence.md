# 永続層（DS / PRS）

> **型**: DS, PRS ／ **必須上流**: DS→P, PRS→DS（activate_stage: design ✅）
> spec-inspector のデータストアと永続化設計（doc-system 設計層）。

## DS-1: in-graph ノードファイル群

<details><summary>⬡ DS-1 · v0.1.0</summary>

```yaml
id: DS-1
type: DS
labels: []
scheduled: ""
edges:
  - to: P-6
    ref_version: "0.2"
```
</details>

**保存対象**: `doc-system/**/*.md` のうち trace_scope（include/exclude）フィルタ適用後に in-graph と判定された対象 .md ファイル集合（D-1 = in-graph 集合）。
**保存理由**: 検査パイプライン（P-1 のノード受付・パース以降）が「どのファイルをノードとして読むか」を確定するため。P-6（in-graph 集合決定）がこの集合を確定し、下流の P-1〜P-4 がここを読んで検査する。
**ライフサイクル**: ACTOR-1（仕様著者）が .md ファイルを作成・編集・削除して集合の実体を変える。spec-inspector は読み取り専用で、P-6 が実行のたびに trace_scope を適用して集合を再導出するのみ（書き込まない）。

## DS-2: config.yaml

<details><summary>⬡ DS-2 · v0.1.0</summary>

```yaml
id: DS-2
type: DS
labels: []
scheduled: ""
edges:
  - to: P-5
    ref_version: "0.2"
```
</details>

**保存対象**: `docs/doc-system/config.yaml`（RULE 設定・必須接続ルール・ステージ状態・抑制対象外・trace_scope など、検査パイプラインの挙動を決める全設定）。
**保存理由**: RULE 発火・抑制・activate_stage 判定の単一ソース。P-5（config 読込・検証）がこのファイルを読んで検証し、下流の全プロセス（P-1〜P-4・P-6）の挙動を駆動する。
**ライフサイクル**: ACTOR-1（仕様著者）が config.yaml を作成・更新・管理する。spec-inspector は読み取り専用で、P-5 が実行のたびに読込・検証するのみ（書き込まない）。

## DS-3: tmp ノード草案

<details><summary>⬡ DS-3 · v0.1.0</summary>

```yaml
id: DS-3
type: DS
labels: []
scheduled: ""
edges:
  - to: P-7
    ref_version: "0.4"
```
</details>

**保存対象**: `tmp/<sprint>/<parent-id>.md`（著作エージェントが書き出す一時的なノード草案ファイル群＝D-8 ノード草案）。
**保存理由**: P-7（著作・反映パイプライン）の中間成果。著作（P-7-1）の出力を検証・反映（P-7-2）が読み取れるよう一時保管する。本ファイルへ反映する前のステージング領域。
**ライフサイクル**: P-7-1-3（草案 tmp 書出）が作成する。reconciliation（P-7-2）が検証後に本ファイルへ転記し、転記完了後は削除可。検査パイプライン（P-1〜P-6）は trace_scope の exclude 範囲外（`docs/**` 以外の tmp）であり in-graph には含まれない。

## PRS-1: tmp 草案ファイル書き出し

<details><summary>⬡ PRS-1 · v0.1.0</summary>

```yaml
id: PRS-1
type: PRS
labels: []
scheduled: ""
edges:
  - to: DS-3
    ref_version: "0.1"
```
</details>

D-8（ノード草案）を `tmp/<sprint>/<parent-id>.md` に .md ファイルとして書き出す永続化。doc-system 記法（summary バッジ・YAML フロントマター・無名依存辺）に準拠したテキストで保存する。
**保存形式**: テキスト .md ファイル（doc-system 記法準拠・1 親ノードにつき 1 ファイル `tmp/<sprint>/<parent-id>.md`）。append-only ではなく親 ID 単位で上書き。
**ライフサイクル**: P-7-1-3（草案 tmp 書出）が著作のたびに作成・上書き。reconciliation（P-7-2）が本ファイルへ反映した後は削除可（一時領域）。
