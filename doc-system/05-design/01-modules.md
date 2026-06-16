# モジュール構成（MOD / PORT）

> **型**: MOD, PORT ／ **必須上流**: P（refines ✅）
> spec-inspector Python パッケージのモジュール構成（doc-system 設計層・activate_stage: design）。
> review-system 本体設計（`docs/design/`）とは別系統。

## 依存規則（1枚）

```
domain ← ports ← core（config/collector/parser/checker/filter/coverage/reporter）
       ← adapters ← __main__（合成ルート）
```

- `core/*` は `ports.*` と `domain.*` だけに依存（adapters/io/filesystem を直接 import しない）
- `adapters/*` が `ports.*` の Protocol を実装（結線は `__main__` のみ）
- テスト用シーム: `FakeFsAdapter`（`adapters/fs.py`）が FileSystemPort を実装

---

## MOD-1: domain

<details><summary>⬡ MOD-1 · v0.1</summary>

```yaml
id: MOD-1
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-1
    ref_version: "0.3"
```
</details>

**パス**: `spec_inspector/domain.py`
**責務**: NodeRecord / EdgeRecord / ViolationRecord / ConfigSlice 等の値オブジェクトを定義する。
**公開 I/F**: `NodeRecord`, `EdgeRecord`, `ViolationRecord`, `ConfigSlice`
**依存**: なし（最下層・他のどの層にも依存しない）
**依存方向**: domain（被依存される最下層）

---

## MOD-2: config

<details><summary>⬡ MOD-2 · v0.1</summary>

```yaml
id: MOD-2
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-5
    ref_version: "0.2"
```
</details>

**パス**: `spec_inspector/config.py`
**責務**: P-5（config 読込・スキーマ検証・スライス組立）を実現する。
**公開 I/F**: `load_config(path) -> ConfigSlice`
**依存**: ports（FileSystemPort）, domain（ConfigSlice）
**依存方向**: core ← domain / ports

---

## MOD-3: collector

<details><summary>⬡ MOD-3 · v0.1</summary>

```yaml
id: MOD-3
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-6
    ref_version: "0.2"
```
</details>

**パス**: `spec_inspector/collector.py`
**責務**: P-6（in-graph 集合決定・include/exclude 適用）を実現する。
**公開 I/F**: `collect_in_graph(root, config) -> list[Path]`
**依存**: ports（FileSystemPort）, domain（ConfigSlice）
**依存方向**: core ← domain / ports

---

## MOD-4: parser

<details><summary>⬡ MOD-4 · v0.1</summary>

```yaml
id: MOD-4
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-1
    ref_version: "0.3"
```
</details>

**パス**: `spec_inspector/parser.py`
**責務**: P-1（ノード受付・パース・ビュー射影 P-1-1〜P-1-6）を実現する。
**公開 I/F**: `parse_nodes(paths) -> list[NodeRecord]`
**依存**: ports（FileSystemPort）, domain（NodeRecord / EdgeRecord）
**依存方向**: core ← domain / ports

---

## MOD-5: checker

<details><summary>⬡ MOD-5 · v0.1</summary>

```yaml
id: MOD-5
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-2
    ref_version: "0.3"
```
</details>

**パス**: `spec_inspector/checker.py`
**責務**: P-2-1〜P-2-4（RULE 違反候補検出）を実現する。
**公開 I/F**: `check(nodes, config) -> list[ViolationRecord]`
**依存**: domain（NodeRecord / ViolationRecord / ConfigSlice）
**依存方向**: core ← domain

---

## MOD-6: filter

<details><summary>⬡ MOD-6 · v0.1</summary>

```yaml
id: MOD-6
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-2-5
    ref_version: "0.1"
```
</details>

**パス**: `spec_inspector/filter.py`
**責務**: P-2-5（抑制・発火フィルタ）を実現する。
**公開 I/F**: `apply_suppression(violations, config) -> list[ViolationRecord]`
**依存**: domain（ViolationRecord / ConfigSlice）
**依存方向**: core ← domain

---

## MOD-7: coverage

<details><summary>⬡ MOD-7 · v0.1</summary>

```yaml
id: MOD-7
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-3
    ref_version: "0.2"
```
</details>

**パス**: `spec_inspector/coverage.py`
**責務**: P-3（カバレッジ点検・P-3-1 / P-3-2）を実現する。
**公開 I/F**: `check_coverage(nodes, config) -> list[ViolationRecord]`
**依存**: domain（NodeRecord / ViolationRecord / ConfigSlice）
**依存方向**: core ← domain

---

## MOD-8: reporter

<details><summary>⬡ MOD-8 · v0.1</summary>

```yaml
id: MOD-8
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-4
    ref_version: "0.2"
```
</details>

**パス**: `spec_inspector/reporter.py`
**責務**: P-4（レポート生成・G# 採番・終了コード決定・P-4-1〜P-4-4）を実現する。
**公開 I/F**: `render_report(violations) -> str`, `exit_code(violations) -> int`
**依存**: domain（ViolationRecord）
**依存方向**: core ← domain

---

## MOD-9: author

<details><summary>⬡ MOD-9 · v0.1</summary>

```yaml
id: MOD-9
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-7
    ref_version: "0.4"
```
</details>

**パス**: `spec_inspector/author.py`
**責務**: P-7（ノード著作・反映・P-7-1 / P-7-2）を実現する。
**公開 I/F**: `author_nodes(...)`, `apply_to_graph(...)`
**依存**: ports（FileSystemPort）, domain（NodeRecord）
**依存方向**: core ← domain / ports

---

## MOD-10: ports

<details><summary>⬡ MOD-10 · v0.1</summary>

```yaml
id: MOD-10
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-1
    ref_version: "0.3"
```
</details>

**パス**: `spec_inspector/ports.py`
**責務**: FileSystemPort 抽象 IF（Protocol）を定義する（P-1 が依存するポート）。
**公開 I/F**: `FileSystemPort`（Protocol）
**依存**: domain のみ（core / adapters / __main__ に依存しない）
**依存方向**: ports ← domain

---

## MOD-11: adapters/fs

<details><summary>⬡ MOD-11 · v0.1</summary>

```yaml
id: MOD-11
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-1
    ref_version: "0.3"
```
</details>

**パス**: `spec_inspector/adapters/fs.py`
**責務**: RealFsAdapter（本番）・FakeFsAdapter（テスト用シーム）として FileSystemPort を実装する。
**公開 I/F**: `RealFsAdapter`, `FakeFsAdapter`
**依存**: ports（FileSystemPort Protocol を実装）
**依存方向**: adapters ← ports

---

## MOD-12: __main__

<details><summary>⬡ MOD-12 · v0.1</summary>

```yaml
id: MOD-12
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-5
    ref_version: "0.2"
```
</details>

**パス**: `spec_inspector/__main__.py`
**責務**: 合成ルート + CLI エントリポイント（DI 結線・コマンドライン引数解析）。
**公開 I/F**: `main(argv) -> int`
**依存**: adapters / core / domain（全層を結線。Protocol 実装の注入はここでのみ行う）
**依存方向**: __main__ ← adapters / core

---

## PORT-1: FileSystemPort

<details><summary>⬡ PORT-1 · v0.1</summary>

```yaml
id: PORT-1
type: PORT
labels: []
scheduled: ""
edges:
  - to: MOD-10
    ref_version: "0.1"
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
