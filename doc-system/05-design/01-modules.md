# モジュール構成（MOD / PORT）

> **型**: MOD, PORT ／ **必須上流**: P（refines ✅）
> spec-inspector Python パッケージのモジュール構成（doc-system 設計層・activate_stage: design）。
> review-system 本体設計（`docs/design/`）とは別系統。

## 依存規則（1枚）

```
domain ← ports ← core（config / collector / parser / projector /
                        drift_checker / structure_checker / condition_checker / verification_checker /
                        filter / graph_coverage / spec_coverage / reporter / author / reconciler）
       ← adapters ← __main__（合成ルート）
```

- `core/*` は `ports.*` と `domain.*` だけに依存（adapters/io/filesystem を直接 import しない）
- `adapters/*` が `ports.*` の Protocol を実装（結線は `__main__` のみ）
- テスト用シーム: `FakeFsAdapter`（`adapters/fs.py`）が FileSystemPort を実装

---

## MOD-1: domain

<details><summary>⬡ MOD-1 · v0.3.0</summary>

```yaml
id: MOD-1
type: MOD
labels: []
scheduled: ""
edges:
  - to: D-4
    ref_version: "0.2.0"
  - to: D-5
    ref_version: "0.1.0"
  - to: D-6
    ref_version: "0.1.0"
  - to: D-7
    ref_version: "0.1.0"
  - to: D-9
    ref_version: "0.2.0"
  - to: D-10
    ref_version: "0.1.0"
  - to: D-11
    ref_version: "0.1.0"
  - to: D-12
    ref_version: "0.1.0"
  - to: D-13
    ref_version: "0.1.0"
  - to: D-14
    ref_version: "0.2.0"
  - to: D-15
    ref_version: "0.1.0"
  - to: D-16
    ref_version: "0.1.0"
  - to: D-17
    ref_version: "0.1.0"
  - to: D-18
    ref_version: "0.1.0"
  - to: D-19
    ref_version: "0.1.0"
  - to: D-20
    ref_version: "0.1.0"
  - to: D-21
    ref_version: "0.1.0"
  - to: FND-96
    ref_version: "0.3.0"
  - to: FND-100
    ref_version: "0.1.0"
```
</details>

**パス**: `spec_inspector/domain.py`
**責務**: NodeRecord / EdgeRecord / ViolationRecord / ConfigSlice / CoverageReport / InspectionViews 等の値オブジェクトを定義する。
**公開 I/F**: `NodeRecord`, `EdgeRecord`, `ViolationRecord`, `ConfigSlice`, `CoverageReport`, `InspectionViews`
**依存**: なし（最下層・他のどの層にも依存しない）
**依存方向**: domain（被依存される最下層）

> **改訂理由（MINOR バンプ v0.1→v0.2）**: FND-96 選択肢A（DM→MOD→D 正規化）。MOD-1 は処理プロセスを実装しないため P-1 辺を削除し、realize するデータ型概念 D-4/D-6/D-9〜D-21 への辺へ変更。`→FND-96` バックリファレンス付与。
>
> **改訂理由（MINOR バンプ v0.2→v0.3）**: PR #32 レビュー対応（DM→MOD→D 対称化・FND-100）。FND-96 処置後に残った DM↔D 被覆の非対称を是正。D-5（パース段違反リスト・DM-3 ViolationRecord が realize）と D-7（カバレッジ計測結果・DM-5 CoverageReport が realize）への realize 辺を追加し、`DM→MOD→D` チェーンの被覆漏れを補完。D-17〜D-21 は既存辺あり（DM-6 InspectionViews が realize）。型変更・構造変更なし（辺追加のみ）のため MINOR。`→FND-100` バックリファレンス付与。

---

## MOD-2: config

<details><summary>⬡ MOD-2 · v0.1.0</summary>

```yaml
id: MOD-2
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-5
    ref_version: "0.2.0"
```
</details>

**パス**: `spec_inspector/config.py`
**責務**: P-5（config 読込・スキーマ検証・スライス組立）を実現する。
**公開 I/F**: `load_config(path) -> ConfigSlice`
**依存**: ports（FileSystemPort）, domain（ConfigSlice）
**依存方向**: core ← domain / ports

---

## MOD-3: collector

<details><summary>⬡ MOD-3 · v0.1.0</summary>

```yaml
id: MOD-3
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-6
    ref_version: "0.2.0"
```
</details>

**パス**: `spec_inspector/collector.py`
**責務**: P-6（in-graph 集合決定・include/exclude 適用）を実現する。
**公開 I/F**: `collect_in_graph(root, config) -> list[Path]`
**依存**: ports（FileSystemPort）, domain（ConfigSlice）
**依存方向**: core ← domain / ports

---

## MOD-4: parser

<details><summary>⬡ MOD-4 · v0.2.0</summary>

```yaml
id: MOD-4
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-1
    ref_version: "0.3.0"
  - to: DD-13
    ref_version: "0.2.0"
```
</details>

**パス**: `spec_inspector/parser.py`
**責務**: P-1-1〜P-1-5（パース・集合組立まで）を実現する。P-1-6（ビュー射影）は MOD-13 が担当。
**公開 I/F**: `parse_nodes(paths) -> list[NodeRecord]`
**依存**: ports（FileSystemPort）, domain（NodeRecord / EdgeRecord）
**依存方向**: core ← domain / ports

> **改訂理由（MINOR バンプ v0.1→v0.2）**: DD-13 改訂（孫プロセスあり OR 責務が明確に別 → L2 単位分割）に伴い、責務を P-1-1〜P-1-5（パース・集合組立まで）に限定。P-1-6（検査ビュー射影＝ビュー工場・別責務）は MOD-13 projector へ分離。

---

## MOD-5: drift_checker

<details><summary>⬡ MOD-5 · v0.2.0</summary>

```yaml
id: MOD-5
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-2-1
    ref_version: "0.2.0"
  - to: DD-13
    ref_version: "0.2.0"
```
</details>

**パス**: `spec_inspector/drift_checker.py`
**責務**: P-2-1（ref_version ドリフト検出・義務辺残存検出）を実現する。
**公開 I/F**: `check_drift(nodes, config) -> list[ViolationRecord]`
**依存**: domain（NodeRecord / ViolationRecord / ConfigSlice）
**依存方向**: core ← domain

> **改訂理由（MINOR バンプ v0.1→v0.2）**: DD-13 改訂に伴い、孫プロセス（P-2-1-1/P-2-1-2）を持つ P-2-1 を単独モジュールへ分割。checker.py → drift_checker.py に改名し、参照先を P-2 → P-2-1 に変更。旧 P-2-2/P-2-3/P-2-4 担当分は MOD-14/15/16 へ分離。

---

## MOD-6: filter

<details><summary>⬡ MOD-6 · v0.1.0</summary>

```yaml
id: MOD-6
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-2-5
    ref_version: "0.1.0"
```
</details>

**パス**: `spec_inspector/filter.py`
**責務**: P-2-5（抑制・発火フィルタ）を実現する。
**公開 I/F**: `apply_suppression(violations, config) -> list[ViolationRecord]`
**依存**: domain（ViolationRecord / ConfigSlice）
**依存方向**: core ← domain

---

## MOD-7: graph_coverage

<details><summary>⬡ MOD-7 · v0.2.0</summary>

```yaml
id: MOD-7
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-3-1
    ref_version: "0.2.0"
  - to: DD-13
    ref_version: "0.2.0"
```
</details>

**パス**: `spec_inspector/graph_coverage.py`
**責務**: P-3-1（グラフ網羅性点検・未駆動出力/未定義反応イベント/未消費入力検出）を実現する。
**公開 I/F**: `check_graph_coverage(nodes, config) -> list[ViolationRecord]`
**依存**: domain（NodeRecord / ViolationRecord / ConfigSlice）
**依存方向**: core ← domain

> **改訂理由（MINOR バンプ v0.1→v0.2）**: DD-13 改訂に伴い、孫プロセス（P-3-1-1〜P-3-1-3）を持つ P-3-1 を単独モジュールへ分割。coverage.py → graph_coverage.py に改名し、参照先を P-3 → P-3-1 に変更。P-3-2（仕様カバレッジ計測）担当分は MOD-17 へ分離。

---

## MOD-8: reporter

<details><summary>⬡ MOD-8 · v0.1.0</summary>

```yaml
id: MOD-8
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-4
    ref_version: "0.2.0"
```
</details>

**パス**: `spec_inspector/reporter.py`
**責務**: P-4（レポート生成・G# 採番・終了コード決定・P-4-1〜P-4-4）を実現する。
**公開 I/F**: `render_report(violations) -> str`, `exit_code(violations) -> int`
**依存**: domain（ViolationRecord）
**依存方向**: core ← domain

---

## MOD-9: author

<details><summary>⬡ MOD-9 · v0.2.0</summary>

```yaml
id: MOD-9
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-7-1
    ref_version: "0.2.0"
  - to: DD-13
    ref_version: "0.2.0"
```
</details>

**パス**: `spec_inspector/author.py`
**責務**: P-7-1（著作・tmp 出力）を実現する。
**公開 I/F**: `author_nodes(...) -> D8Draft`
**依存**: ports（FileSystemPort）, domain（NodeRecord）
**依存方向**: core ← domain / ports

> **改訂理由（MINOR バンプ v0.1→v0.2）**: DD-13 改訂に伴い、孫プロセス（P-7-1-1〜P-7-1-3）を持つ P-7-1 を単独モジュールに限定。参照先を P-7 → P-7-1（著作側のみ）に変更。P-7-2（調停・本ファイル反映）担当分は MOD-18 reconciler へ分離。

---

## MOD-10: ports

<details><summary>⬡ MOD-10 · v0.1.0</summary>

```yaml
id: MOD-10
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-1
    ref_version: "0.3.0"
```
</details>

**パス**: `spec_inspector/ports.py`
**責務**: FileSystemPort 抽象 IF（Protocol）を定義する（P-1 が依存するポート）。
**公開 I/F**: `FileSystemPort`（Protocol）
**依存**: domain のみ（core / adapters / __main__ に依存しない）
**依存方向**: ports ← domain

---

## MOD-11: adapters/fs

<details><summary>⬡ MOD-11 · v0.1.0</summary>

```yaml
id: MOD-11
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-1
    ref_version: "0.3.0"
```
</details>

**パス**: `spec_inspector/adapters/fs.py`
**責務**: RealFsAdapter（本番）・FakeFsAdapter（テスト用シーム）として FileSystemPort を実装する。
**公開 I/F**: `RealFsAdapter`, `FakeFsAdapter`
**依存**: ports（FileSystemPort Protocol を実装）
**依存方向**: adapters ← ports

---

## MOD-12: __main__

<details><summary>⬡ MOD-12 · v0.1.0</summary>

```yaml
id: MOD-12
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-5
    ref_version: "0.2.0"
```
</details>

**パス**: `spec_inspector/__main__.py`
**責務**: 合成ルート + CLI エントリポイント（DI 結線・コマンドライン引数解析）。
**公開 I/F**: `main(argv) -> int`
**依存**: adapters / core / domain（全層を結線。Protocol 実装の注入はここでのみ行う）
**依存方向**: __main__ ← adapters / core

---

## MOD-13: projector

<details><summary>⬡ MOD-13 · v0.1.0</summary>

```yaml
id: MOD-13
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-1-6
    ref_version: "0.1.0"
  - to: DD-13
    ref_version: "0.2.0"
```
</details>

**パス**: `spec_inspector/projector.py`
**責務**: P-1-6（検査ビュー射影）を実現する。D-4（構造化ノードセット）を消費スライス D-17〜D-21 へ射影する。
**公開 I/F**: `project_views(node_set) -> InspectionViews`
**依存**: domain（NodeRecord / 各消費スライス値オブジェクト）
**依存方向**: core ← domain

> **改訂理由（新設・DD-13 改訂）**: P-1-6（検査ビュー射影）は孫プロセスを持たないが「ビュー工場」として責務が独立するため、parser.py（MOD-4）から分離して新設。

---

## MOD-14: structure_checker

<details><summary>⬡ MOD-14 · v0.1.0</summary>

```yaml
id: MOD-14
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-2-2
    ref_version: "0.2.0"
  - to: DD-13
    ref_version: "0.2.0"
```
</details>

**パス**: `spec_inspector/structure_checker.py`
**責務**: P-2-2（構造完結性検査・孤立/dangling/必須辺/階層親不在検出）を実現する。
**公開 I/F**: `check_structure(nodes, config) -> list[ViolationRecord]`
**依存**: domain（NodeRecord / ViolationRecord / ConfigSlice）
**依存方向**: core ← domain

> **改訂理由（新設・DD-13 改訂）**: 孫プロセス（P-2-2-1〜P-2-2-4）を持つ P-2-2 を単独モジュールへ分割。旧 checker.py（MOD-5）担当分の構造完結性検査を独立化。

---

## MOD-15: condition_checker

<details><summary>⬡ MOD-15 · v0.1.0</summary>

```yaml
id: MOD-15
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-2-3
    ref_version: "0.2.0"
  - to: DD-13
    ref_version: "0.2.0"
```
</details>

**パス**: `spec_inspector/condition_checker.py`
**責務**: P-2-3（カバレッジ属性検査・condition 語彙/FR normal/FR failure-error/TD-SPEC 整合検出）を実現する。
**公開 I/F**: `check_conditions(nodes, config) -> list[ViolationRecord]`
**依存**: domain（NodeRecord / ViolationRecord / ConfigSlice）
**依存方向**: core ← domain

> **改訂理由（新設・DD-13 改訂）**: 孫プロセス（P-2-3-1〜P-2-3-4）を持つ P-2-3 を単独モジュールへ分割。旧 checker.py（MOD-5）担当分のカバレッジ属性検査を独立化。

---

## MOD-16: verification_checker

<details><summary>⬡ MOD-16 · v0.1.0</summary>

```yaml
id: MOD-16
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-2-4
    ref_version: "0.2.0"
  - to: DD-13
    ref_version: "0.2.0"
```
</details>

**パス**: `spec_inspector/verification_checker.py`
**責務**: P-2-4（検証層完結性検査・FND-TC-VERIFY 必須辺/TR result/TR log_ref 検出）を実現する。
**公開 I/F**: `check_verification(nodes, config) -> list[ViolationRecord]`
**依存**: domain（NodeRecord / ViolationRecord / ConfigSlice）
**依存方向**: core ← domain

> **改訂理由（新設・DD-13 改訂）**: 孫プロセス（P-2-4-1〜P-2-4-3）を持つ P-2-4 を単独モジュールへ分割。旧 checker.py（MOD-5）担当分の検証層完結性検査を独立化。

---

## MOD-17: spec_coverage

<details><summary>⬡ MOD-17 · v0.1.0</summary>

```yaml
id: MOD-17
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-3-2
    ref_version: "0.2.0"
  - to: DD-13
    ref_version: "0.2.0"
```
</details>

**パス**: `spec_inspector/spec_coverage.py`
**責務**: P-3-2（仕様カバレッジ計測・FR×condition 充足集計・テーブル整形）を実現する。
**公開 I/F**: `measure_spec_coverage(nodes, config) -> CoverageReport`
**依存**: domain（NodeRecord / CoverageReport / ConfigSlice）
**依存方向**: core ← domain

> **改訂理由（新設・DD-13 改訂）**: 孫プロセス（P-3-2-1〜P-3-2-2）を持つ P-3-2 を単独モジュールへ分割。旧 coverage.py（MOD-7）担当分の仕様カバレッジ計測を独立化。

---

## MOD-18: reconciler

<details><summary>⬡ MOD-18 · v0.1.0</summary>

```yaml
id: MOD-18
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-7-2
    ref_version: "0.2.0"
  - to: DD-13
    ref_version: "0.2.0"
```
</details>

**パス**: `spec_inspector/reconciler.py`
**責務**: P-7-2（調停・本ファイル反映・草案スキーマ検証・転記）を実現する。
**公開 I/F**: `reconcile(draft_path, target_path) -> None`
**依存**: ports（FileSystemPort）, domain（NodeRecord）
**依存方向**: core ← domain / ports

> **改訂理由（新設・DD-13 改訂）**: 孫プロセス（P-7-2-1〜P-7-2-2）を持つ P-7-2 を単独モジュールへ分割。旧 author.py（MOD-9）担当分の調停・本ファイル反映を独立化。

---

## PORT-1: FileSystemPort

<details><summary>⬡ PORT-1 · v0.1.0</summary>

```yaml
id: PORT-1
type: PORT
labels: []
scheduled: ""
edges:
  - to: MOD-10
    ref_version: "0.1.0"
```
</details>

```python
class FileSystemPort(Protocol):
    def list_md_files(self, root: Path) -> list[Path]: ...
    def read_file(self, path: Path) -> str: ...
```

**目的**: ファイルシステム副作用（`.md` ファイル列挙・読み出し）を抽象化し、core を実 I/O から切り離す。
**方向**: driven（外向き・副作用を抽象化）
**実装アダプタ**: RealFsAdapter（本番）/ FakeFsAdapter（テスト用シーム）
