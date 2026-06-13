> 反映先: doc-system/03-analysis/03-processes.md（P-7 配下・親 P-7 は reconciliation が書き換え）

### P-7-1: 著作・tmp 出力

<details><summary>⬡ P-7-1 · v0.1</summary>

```yaml
id: P-7-1
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-38
    ref_version: "0.3"
  - to: I-7
    ref_version: "0.6"
  - to: E-2
    ref_version: "0.5"
```
</details>

仕様著者（ACTOR-1）がテンプレート（I-7）と著作エージェント（P-7 の内部定義）を用いてノードを著作し、`tmp/<sprint>/<parent-id>.md` に草案を出力する。
**入力**: I-7（テンプレート参照）を消費（P→I）
**出力**: ノード草案（tmp ファイル・P-7-2 へ）
**トリガ**: E-2 に依存（P→E・著作要求）

---

### P-7-2: 調停・本ファイル反映

<details><summary>⬡ P-7-2 · v0.1</summary>

```yaml
id: P-7-2
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-39
    ref_version: "0.3"
  - to: E-2
    ref_version: "0.5"
```
</details>

reconciliation エージェントが P-7-1 の tmp 草案を検証（id 欠如等の検出）し、整合確認の上 doc-system 本ファイルへ転記して O-3（著作済みノードファイル）を生成する。
**入力**: P-7-1 からの tmp 草案
**出力**: O-3（著作済みノードファイル）が P-7-2 に依存（O→P）——著作者（ACTOR-1）が受け取る
**トリガ**: E-2 に依存（P→E・P-7-1 完了後）

---
