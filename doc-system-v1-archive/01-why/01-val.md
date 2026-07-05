# 価値命題

> **型**: VAL ／ **必須上流**: なし（Why 層の頂点）

---

## VAL-1: トレーサビリティ

<details><summary>⬡ VAL-1 · v0.1.0</summary>

```yaml
id: VAL-1
type: VAL
labels: []
scheduled: ""
edges: []
```
</details>

仕様著者・レビュアー・実装者が、要件から実装・テストまでを**双方向に** ID でたどれることで、上流→下流の抜け検出と、後工程の修正・指摘が影響する上流ノードの特定の両方ができる。

---

## VAL-2: 自動整合性検証

<details><summary>⬡ VAL-2 · v0.1.0</summary>

```yaml
id: VAL-2
type: VAL
labels: []
scheduled: ""
edges: []
```
</details>

ルールベースの自動点検（spec-inspector）が、人手レビューに頼らずに整合性違反を列挙できる。

---

## VAL-3: 著作効率

<details><summary>⬡ VAL-3 · v0.1.0</summary>

```yaml
id: VAL-3
type: VAL
labels: []
scheduled: ""
edges: []
```
</details>

工程別スキルが著作規約を内包することで、著者が別ファイルを参照せずにノードを正しく書ける。

---

## VAL-4: 段階的前進

<details><summary>⬡ VAL-4 · v0.1.0</summary>

```yaml
id: VAL-4
type: VAL
labels: []
scheduled: ""
edges: []
```
</details>

全層を一度に揃えなくても、現フェーズ・現ステージの対象だけを検査し、未来フェーズのノードを警告ノイズなく前進できる。

---

## VAL-5: グラフの図的可視化

<details><summary>⬡ VAL-5 · v0.1.0</summary>

```yaml
id: VAL-5
type: VAL
labels: []
scheduled: "sprint-2"
edges: []
```
</details>

ノードグラフから標準図（DFD・クラス図等）を機械生成し、ノード間の依存・データフローを可視化することで、レビュアー・メンテナが関係性を俯瞰し、開発の意思決定を支援できる。

---

## VAL-6: 図からの逆起こし（往復）

<details><summary>⬡ VAL-6 · v0.1.0</summary>

```yaml
id: VAL-6
type: VAL
labels: []
scheduled: "sprint-2"
edges: []
```
</details>

既存ドキュメントの図からノードグラフを機械的に逆起こしし、図とノードグラフの往復・既存図資産の取り込みを可能にする。
