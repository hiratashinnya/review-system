# 論理プロセス

> **型**: P ／ **必須上流**: SPEC（依存辺 ✅）
> 依存方向（DD-017）：P→I/P→D（消費）・P→E（トリガ事象に依存）。
> 生成（O→P・D→P）は O/D 側に辺を持つ（P 側には produces を書かない）。

---

## P-1: ノード受付・パース

<details><summary>⬡ P-1 · v0.3.0</summary>

```yaml
id: P-1
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-1
    ref_version: "0.3"
  - to: SPEC-2
    ref_version: "0.3"
  - to: D-1
    ref_version: "0.1"
  - to: D-9
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
  - to: FND-1
    ref_version: "0.1"
  - to: FND-20
    ref_version: "0.1"
  - to: DD-7
    ref_version: "0.1"
```
</details>

（P-1-1: ファイル読込 / P-1-2: マーカー走査 / P-1-3: YAML パース / P-1-4: スキーマ検証 / P-1-5: 構造化集合組立 / P-1-6: 検査ビュー射影 に責務を委譲）in-graph ファイル集合をノード単位にパースして消費スライス（D-17〜D-21・D-5）へ射影する親プロセス。消費入力の明示は各子プロセスに移す。旧 I-1（直接入力）・旧 D-3 依存を整理し、I-1 の消費はリーフ P-1-1 が担い、D-4 は P-1 内部の正規化集合として保持して外部配布は D-17〜D-21・D-5 が担う（FND-21）。
**トリガ**: E-1 に依存（P→E）

---

### P-1-1: ファイル読込

<details><summary>⬡ P-1-1 · v0.1.0</summary>

```yaml
id: P-1-1
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-1
    ref_version: "0.3"
  - to: I-1
    ref_version: "0.1"
  - to: D-1
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

D-1 に含まれる各ファイル（I-1：ノードファイル群）を UTF-8 で読み込み、ファイル本文（テキスト文字列）を生成する。
**責務（単一動詞）**: ファイルをバイト列から UTF-8 テキストへ読み込む
**提供価値**: パース入力の供給——ファイル読込エラー（存在しない・文字コード不正）を後段から切り離して早期検出できる
**入力**: I-1（ノードファイル群）・D-1（in-graph ファイル集合）を消費（P→I/P→D）
**出力**: ファイル本文（P-1-2 が消費する P-1 内部中間物）が生成される
**トリガ**: E-1 に依存（P→E）

---

### P-1-2: マーカー走査

<details><summary>⬡ P-1-2 · v0.1.0</summary>

```yaml
id: P-1-2
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-32
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

ファイル本文を走査し、`⬡ PREFIX-N` マーカー行と直後 YAML ブロックの位置（行番号・バイトオフセット）を特定する。RULE-024（マーカー直後 YAML 欠如）の違反候補を検出する。
**責務（単一動詞）**: マーカーと直後 YAML ブロック位置を走査・特定する
**提供価値**: ノード境界の確定——後段 YAML パースが確定した範囲だけを処理できる
**入力**: ファイル本文（P-1-1 が生成する P-1 内部中間物）を消費
**出力**: マーカー＋ブロック位置リスト・RULE-024 違反候補（P-1-3 が消費 / D-5 素材として P-1-5 が収集する P-1 内部中間物）が生成される
**トリガ**: E-1 に依存（P→E）

---

### P-1-3: YAML パース

<details><summary>⬡ P-1-3 · v0.1.0</summary>

```yaml
id: P-1-3
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-2
    ref_version: "0.3"
  - to: E-1
    ref_version: "0.5"
```
</details>

P-1-2 が特定した YAML ブロックを PyYAML safe_load でパースしノード辞書を生成する。パース不能（RULE-023・fail-close）を検出する。
**責務（単一動詞）**: YAML ブロックをノード辞書へパースする
**提供価値**: 構造化の核——テキスト表現を操作可能なデータ構造へ変換する
**入力**: マーカー＋ブロック位置リスト（P-1-2 が生成する P-1 内部中間物）を消費
**出力**: ノード辞書・RULE-023 違反候補（P-1-4 が消費 / D-5 素材として P-1-5 が収集する P-1 内部中間物）が生成される
**トリガ**: E-1 に依存（P→E）

---

### P-1-4: スキーマ検証

<details><summary>⬡ P-1-4 · v0.1.0</summary>

```yaml
id: P-1-4
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-33
    ref_version: "0.1"
  - to: SPEC-34
    ref_version: "0.1"
  - to: SPEC-35
    ref_version: "0.1"
  - to: SPEC-36
    ref_version: "0.1"
  - to: SPEC-52
    ref_version: "0.1"
  - to: SPEC-53
    ref_version: "0.1"
  - to: D-9
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

ノード辞書の id / type / ref_version / 共通必須フィールド・型・scheduled 値ドメイン・テンプレ由来必須フィールドを検証する（RULE-025/026/027/028/029）。scheduled の値ドメイン照合は D-9 の phases リストを使う。RULE-025/026（テンプレ由来必須フィールド欠如・SPEC-36）の検出もここで担う。
**責務（単一動詞）**: ノード辞書のスキーマを検証する
**提供価値**: フィールドスキーマの in-graph 化保証——型不正・必須欠如を持つノードが後段検査に持ち込まれない
**入力**: ノード辞書（P-1-3 が生成する P-1 内部中間物）・D-9（フェーズ・ステージ状態・scheduled 値ドメイン照合用）を消費（P→D）
**出力**: 検証済みノード・パース段違反候補（P-1-5 が消費 / D-5 素材として P-1-5 が収集する P-1 内部中間物）が生成される
**トリガ**: E-1 に依存（P→E）

---

### P-1-5: 構造化集合組立

<details><summary>⬡ P-1-5 · v0.1.0</summary>

```yaml
id: P-1-5
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-1
    ref_version: "0.3"
  - to: E-1
    ref_version: "0.5"
```
</details>

スキーマ検証通過ノードを D-4（内部正規化集合）へ集約し、P-1-2/1-3/1-4 が検出したパース段違反候補を D-5 として確定する。
**責務（単一動詞）**: 検証通過ノードを正規化集合（D-4）へ集約する
**提供価値**: 後段共通の正規化集合の供給——P-1-6 が射影の基底として使う単一ソースを確立する
**入力**: 検証済みノード・パース段違反候補（P-1-2/1-3/1-4 が生成する P-1 内部中間物）を消費
**出力**: D-4（構造化ノードセット・P-1 内部の正規化集合）・D-5（パース段違反リスト）が生成元 P-1 に依存（D→P）
**トリガ**: E-1 に依存（P→E）

---

### P-1-6: 検査ビュー射影

<details><summary>⬡ P-1-6 · v0.1.0</summary>

```yaml
id: P-1-6
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-1
    ref_version: "0.3"
  - to: E-1
    ref_version: "0.5"
```
</details>

D-4（構造化ノードセット）を消費スライス D-17〜D-21（post-mvp: D-22）へ射影し、各検査・点検プロセスへ必要な属性断片だけを配布する。
**責務（単一動詞）**: D-4 を消費スライスへ射影する
**提供価値**: スタンプ結合の解消——P-2/P-3 系が D-4 全体を受け取る代わりに、各消費先は自分の検査に必要なフィールド断片だけを受け取る
**入力**: D-4（構造化ノードセット・P-1-5 が生成する P-1 内部中間物）を消費
**出力**: D-17（接続検査ビュー）・D-18（属性検査ビュー）・D-19（決定辺ビュー）・D-20（分析層トポロジビュー）・D-21（仕様カバレッジビュー）が生成元 P-1 に依存（D→P）。post-mvp: D-22（グラフトポロジビュー）
**トリガ**: E-1 に依存（P→E）

---

## P-2: RULE 検査

<details><summary>⬡ P-2 · v0.3.0</summary>

```yaml
id: P-2
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-5
    ref_version: "0.2"
  - to: FND-2
    ref_version: "0.1"
```
</details>

（P-2-1〜P-2-5 に責務を委譲）SPEC-5 の通過条件が揃った状態を確認する親プロセス。消費入力の明示は各子プロセスへ移す。P-2-5（抑制・発火フィルタ）を新設し、suppress/scheduled/activate_stage/always_error の適用を P-2-1〜P-2-4 から分離して集約する。

---

### P-2-1: ドリフト・義務辺検査

<details><summary>⬡ P-2-1 · v0.2.0</summary>

```yaml
id: P-2-1
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-9
    ref_version: "0.2"
  - to: SPEC-12
    ref_version: "0.2"
  - to: SPEC-13
    ref_version: "0.2"
  - to: E-1
    ref_version: "0.5"
```
</details>

（P-2-1-1: ref_version ドリフト検出・P-2-1-2: 決定スパイン義務辺残存検出 に責務を委譲）辺の ref_version ドリフトと決定スパインの義務辺残存を担う親プロセス。消費入力（D-19・D-11）の明示は各子へ移す。各子は「論理違反候補」を出力し、抑制適用は P-2-5 が担う。

---

### P-2-1-1: ref_version ドリフト検出

<details><summary>⬡ P-2-1-1 · v0.1.0</summary>

```yaml
id: P-2-1-1
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-9-1
    ref_version: "0.1"
  - to: SPEC-10-1
    ref_version: "0.1"
  - to: D-19
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

決定辺ビュー（D-19）の各辺について ref_version と参照先ノードバッジの x.y を比較し、不一致を RULE-004 ドリフト違反候補として出力する。
**責務（単一動詞）**: 辺 ref_version と参照先バッジの不一致を検出する
**提供価値**: ドリフトした辺を可視化し、反映漏れを機械的に発見できる
**入力**: D-19（決定辺ビュー・edges.ref_version と参照先バッジを含む・P-1-6 が生成）を消費（P→D）
**出力**: ref_version ドリフト違反候補（P-2-5 へ送出）
**トリガ**: E-1 に依存（P→E）

---

### P-2-1-2: 決定スパイン義務辺残存検出

<details><summary>⬡ P-2-1-2 · v0.1.0</summary>

```yaml
id: P-2-1-2
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-12
    ref_version: "0.2"
  - to: SPEC-13
    ref_version: "0.2"
  - to: SPEC-55
    ref_version: "0.1"
  - to: D-19
    ref_version: "0.1"
  - to: D-11
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

決定辺ビュー（D-19）と決定スパイン規則（D-11）を照合し、DD/Q/PEND ノードの義務辺が残存している（反映未完了）ものを RULE-001/002/022 違反候補として出力する。
**責務（単一動詞）**: 決定スパイン対象型（DD/Q/PEND）の義務辺残存を検出する
**提供価値**: 意思決定の反映漏れを機械的に発見し、設計根拠の消失を防止できる
**入力**: D-19（決定辺ビュー・P-1-6 が生成）・D-11（決定スパイン規則・P-5-3 が生成）を消費（P→D）
**出力**: 義務辺残存違反候補（P-2-5 へ送出）
**トリガ**: E-1 に依存（P→E）

---

### P-2-2: 構造完結性検査

<details><summary>⬡ P-2-2 · v0.2.0</summary>

```yaml
id: P-2-2
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-6
    ref_version: "0.2"
  - to: SPEC-7
    ref_version: "0.2"
  - to: SPEC-8
    ref_version: "0.2"
  - to: E-1
    ref_version: "0.5"
```
</details>

（P-2-2-1: 孤立ノード検出・P-2-2-2: 存在しない ID 参照検出・P-2-2-3: 必須辺欠如検出・P-2-2-4: 階層親不在検出 に責務を委譲）グラフの構造的健全性の検査を担う親プロセス。消費入力（D-17・D-10）の明示は各子へ移す。各子は「構造違反候補」を出力し、抑制適用は P-2-5 が担う。I-1-1/I-1-2 への依存辺は D-18（属性検査ビュー）が P-2-5 経由で代替するため削除。

---

### P-2-2-1: 孤立ノード検出

<details><summary>⬡ P-2-2-1 · v0.1.0</summary>

```yaml
id: P-2-2-1
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-7
    ref_version: "0.2"
  - to: D-17
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

接続検査ビュー（D-17）の全ノードを走査し、in/out 辺が共に 0 本のノードを RULE-005 孤立違反候補として出力する。
**責務（単一動詞）**: 辺を持たない孤立ノードを検出する
**提供価値**: 価値経路に接続されていないノードを可視化し、未接続の設計欠落を排除できる
**入力**: D-17（接続検査ビュー・id/type/edges.to を含む・P-1-6 が生成）を消費（P→D）
**出力**: 孤立違反候補（P-2-5 へ送出）
**トリガ**: E-1 に依存（P→E）

---

### P-2-2-2: 存在しない ID 参照検出

<details><summary>⬡ P-2-2-2 · v0.1.0</summary>

```yaml
id: P-2-2-2
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-6-1
    ref_version: "0.1"
  - to: SPEC-6-2
    ref_version: "0.1"
  - to: D-17
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

接続検査ビュー（D-17）の全辺について edges.to の値が in-graph ノードセットに実在する ID かを照合し、存在しない ID を RULE-007 違反候補として出力する。
**責務（単一動詞）**: 辺 to が実在しない dangling 参照を検出する
**提供価値**: 参照先が存在しない辺（dangling edge）を排除し、グラフの参照整合性を保証できる
**入力**: D-17（接続検査ビュー・id および edges.to を含む・P-1-6 が生成）を消費（P→D）
**出力**: dangling 参照違反候補（P-2-5 へ送出）
**トリガ**: E-1 に依存（P→E）

---

### P-2-2-3: 必須辺欠如検出

<details><summary>⬡ P-2-2-3 · v0.2.0</summary>

```yaml
id: P-2-2-3
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-8
    ref_version: "0.2"
  - to: SPEC-15-1
    ref_version: "0.1"
  - to: D-17
    ref_version: "0.1"
  - to: D-10
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
  - to: FND-94
    ref_version: "0.1"
```
</details>

接続検査ビュー（D-17）と必須接続規則（D-10：must_link_to/must_be_linked_from）を照合し、充足していないノードを RULE-006 必須辺欠如違反候補として出力する。RULE-006 のうち SPEC←TD 被依存辺欠如（`must_be_linked_from: SPEC ← [TD]`・旧 RULE-015）も D-10 に含まれる規則として本プロセスが担当するため、failure 系仕様 **SPEC-15-1**（SPEC への TD 被依存辺欠如報告）を詳細化する（FND-94 G1 で SPEC-15-1 の被覆主体として接続・孤児解消）。
**責務（単一動詞）**: must_link_to/must_be_linked_from の必須辺充足を検査して欠如を検出する
**提供価値**: 型別に義務付けられた依存辺の欠落を可視化し、接続の強制を保証できる
**入力**: D-17（接続検査ビュー・P-1-6 が生成）・D-10（必須接続規則・P-5-3 が生成）を消費（P→D）
**出力**: 必須辺欠如違反候補（P-2-5 へ送出）
**トリガ**: E-1 に依存（P→E）

---

### P-2-2-4: 階層親不在検出

<details><summary>⬡ P-2-2-4 · v0.1.0</summary>

```yaml
id: P-2-2-4
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-4
    ref_version: "0.2"
  - to: D-17
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

接続検査ビュー（D-17）の各ノードについて `PREFIX-N-M` パターンの階層 ID を持つものを識別し、親 ID（`PREFIX-N`）が in-graph ノードセットに存在するかを確認して不在の場合を RULE-008 違反候補として出力する。
**責務（単一動詞）**: 階層 ID パターンを持つノードの親 ID の存在有無を検出する
**提供価値**: 親なし孤児階層ノードを排除し、ID 階層の整合性を保証できる
**入力**: D-17（接続検査ビュー・階層 ID パターンを含む・P-1-6 が生成）を消費（P→D）
**出力**: 階層親不在違反候補（P-2-5 へ送出）
**トリガ**: E-1 に依存（P→E）

---

### P-2-3: カバレッジ属性検査

<details><summary>⬡ P-2-3 · v0.2.0</summary>

```yaml
id: P-2-3
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-15
    ref_version: "0.2"
  - to: SPEC-16
    ref_version: "0.2"
  - to: E-1
    ref_version: "0.5"
```
</details>

（P-2-3-1: condition 属性・語彙検査・P-2-3-2: FR normal SPEC 網羅検査・P-2-3-3: FR failure-error SPEC 網羅検査・P-2-3-4: TD-SPEC condition 整合検査 に責務を委譲）SPEC・TD の condition 属性と FR 配下の condition 網羅を担う親プロセス。消費入力（D-18・D-13）の明示は各子へ移す。各子は「カバレッジ属性違反候補」を出力し、抑制適用は P-2-5 が担う。

---

### P-2-3-1: condition 属性・語彙検査

<details><summary>⬡ P-2-3-1 · v0.1.0</summary>

```yaml
id: P-2-3-1
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-15-2
    ref_version: "0.1"
  - to: D-18
    ref_version: "0.1"
  - to: D-13
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

属性検査ビュー（D-18）から SPEC/TD ノードを抽出し、condition 属性の存在と condition 語彙・網羅規則（D-13：condition_vocab）との一致を確認して RULE-016 違反候補を出力する。
**責務（単一動詞）**: SPEC/TD の condition 属性の存在と語彙の正当性を検出する
**提供価値**: condition が未設定または語彙外の値を持つ SPEC/TD を排除し、カバレッジ集計の健全性を保証できる
**入力**: D-18（属性検査ビュー・condition 属性を含む・P-1-6 が生成）・D-13（condition 語彙・網羅規則・P-5-3 が生成）を消費（P→D）
**出力**: condition 属性・語彙違反候補（P-2-5 へ送出）
**トリガ**: E-1 に依存（P→E）

---

### P-2-3-2: FR normal SPEC 網羅検査

<details><summary>⬡ P-2-3-2 · v0.1.0</summary>

```yaml
id: P-2-3-2
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-16-1
    ref_version: "0.1"
  - to: D-18
    ref_version: "0.1"
  - to: D-13
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

属性検査ビュー（D-18）から FR ノードを抽出し、FR 配下に condition: normal の SPEC が存在するかを coverage_rules（D-13）に従って確認して RULE-017 違反候補を出力する。
**責務（単一動詞）**: FR 配下の normal SPEC の欠如を検出する
**提供価値**: 正常系仕様の欠落を可視化し、全 FR が最低限の正常系仕様を持つことを保証できる
**入力**: D-18（属性検査ビュー・FR/SPEC と condition 属性を含む・P-1-6 が生成）・D-13（condition 語彙・網羅規則・P-5-3 が生成）を消費（P→D）
**出力**: FR normal SPEC 欠如違反候補（P-2-5 へ送出）
**トリガ**: E-1 に依存（P→E）

---

### P-2-3-3: FR failure-error SPEC 網羅検査

<details><summary>⬡ P-2-3-3 · v0.1.0</summary>

```yaml
id: P-2-3-3
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-16-2
    ref_version: "0.1"
  - to: D-18
    ref_version: "0.1"
  - to: D-13
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

属性検査ビュー（D-18）から FR ノードを抽出し、FR 配下に condition: failure または condition: error の SPEC が存在するかを coverage_rules（D-13）に従って確認して RULE-018 違反候補を出力する。
**責務（単一動詞）**: FR 配下の failure/error SPEC の欠如を検出する
**提供価値**: 異常系仕様の欠落を可視化し、FR が failure/error 条件の仕様を持つことを促進できる
**入力**: D-18（属性検査ビュー・FR/SPEC と condition 属性を含む・P-1-6 が生成）・D-13（condition 語彙・網羅規則・P-5-3 が生成）を消費（P→D）
**出力**: FR failure-error SPEC 欠如違反候補（P-2-5 へ送出）
**トリガ**: E-1 に依存（P→E）

---

### P-2-3-4: TD-SPEC condition 整合検査

<details><summary>⬡ P-2-3-4 · v0.1.0</summary>

```yaml
id: P-2-3-4
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-15-3
    ref_version: "0.1"
  - to: D-18
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

属性検査ビュー（D-18）から TD ノードを抽出し、TD の condition が verifies 先 SPEC の condition と一致するかを確認して RULE-019 違反候補を出力する。
**責務（単一動詞）**: TD の condition と verifies 先 SPEC の condition の不一致を検出する
**提供価値**: テスト設計のテスト条件と仕様の条件がずれた状態を排除し、テストと仕様の整合性を保証できる
**入力**: D-18（属性検査ビュー・TD/SPEC と condition 属性・verifies 辺を含む・P-1-6 が生成）を消費（P→D）
**出力**: TD-SPEC condition 不整合違反候補（P-2-5 へ送出）
**トリガ**: E-1 に依存（P→E）

---

### P-2-4: 検証層完結性検査

<details><summary>⬡ P-2-4 · v0.2.0</summary>

```yaml
id: P-2-4
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-17
    ref_version: "0.2"
  - to: SPEC-18
    ref_version: "0.2"
  - to: SPEC-19
    ref_version: "0.2"
  - to: E-1
    ref_version: "0.5"
```
</details>

（P-2-4-1: FND-TC-VERIFY 必須辺検査・P-2-4-2: TR result 属性検査・P-2-4-3: TR log_ref 属性検査 に責務を委譲）検証層ノード（FND/TC/VERIFY/TR）の辺と属性の完結性を担う親プロセス。消費入力（D-18・D-10）の明示は各子へ移す。各子は「検証層違反候補」を出力し、抑制適用は P-2-5 が担う。

---

### P-2-4-1: FND-TC-VERIFY 必須辺検査

<details><summary>⬡ P-2-4-1 · v0.1.0</summary>

```yaml
id: P-2-4-1
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-18-1
    ref_version: "0.1"
  - to: SPEC-18-2
    ref_version: "0.1"
  - to: SPEC-18-3
    ref_version: "0.1"
  - to: SPEC-18-4
    ref_version: "0.1"
  - to: SPEC-18-5
    ref_version: "0.1"
  - to: D-18
    ref_version: "0.1"
  - to: D-10
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

属性検査ビュー（D-18）から FND/TC/VERIFY ノードを抽出し、必須接続規則（D-10：must_link_to/must_be_linked_from の verification 行）に照らして必須辺の充足を確認して RULE-006 verification 違反候補を出力する。
**責務（単一動詞）**: 検証層ノード（FND/TC/VERIFY）の必須辺の欠如を検出する
**提供価値**: 検証層の接続完結性を保証し、FND が対象ノードへ、TC が仕様へ、VERIFY が TC へ接続されていることを機械的に確認できる
**入力**: D-18（属性検査ビュー・FND/TC/VERIFY と辺を含む・P-1-6 が生成）・D-10（必須接続規則・P-5-3 が生成）を消費（P→D）
**出力**: FND-TC-VERIFY 必須辺欠如違反候補（P-2-5 へ送出）
**トリガ**: E-1 に依存（P→E）

---

### P-2-4-2: TR result 属性検査

<details><summary>⬡ P-2-4-2 · v0.1.0</summary>

```yaml
id: P-2-4-2
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-19-1
    ref_version: "0.1"
  - to: D-18
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

属性検査ビュー（D-18）から TR ノードを抽出し、result 属性が存在するかを確認して RULE-020 違反候補を出力する。
**責務（単一動詞）**: TR ノードの result 属性の欠如を検出する
**提供価値**: 結果のない TR を排除し、テスト報告が必ず結果を持つことを保証できる
**入力**: D-18（属性検査ビュー・TR と result 属性を含む・P-1-6 が生成）を消費（P→D）
**出力**: TR result 属性欠如違反候補（P-2-5 へ送出）
**トリガ**: E-1 に依存（P→E）

---

### P-2-4-3: TR log_ref 属性検査

<details><summary>⬡ P-2-4-3 · v0.1.0</summary>

```yaml
id: P-2-4-3
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-19-2
    ref_version: "0.1"
  - to: D-18
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

属性検査ビュー（D-18）から TR ノードを抽出し、log_ref 属性が存在するかを確認して RULE-021 違反候補を出力する。
**責務（単一動詞）**: TR ノードの log_ref 属性の欠如を検出する
**提供価値**: 証跡なき TR を排除し、テスト報告が必ず実施証跡への参照を持つことを保証できる
**入力**: D-18（属性検査ビュー・TR と log_ref 属性を含む・P-1-6 が生成）を消費（P→D）
**出力**: TR log_ref 属性欠如違反候補（P-2-5 へ送出）
**トリガ**: E-1 に依存（P→E）

---

### P-2-5: 抑制・発火フィルタ

<details><summary>⬡ P-2-5 · v0.1.0</summary>

```yaml
id: P-2-5
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-20
    ref_version: "0.2"
  - to: SPEC-21
    ref_version: "0.3"
  - to: D-9
    ref_version: "0.1"
  - to: D-12
    ref_version: "0.1"
  - to: D-14
    ref_version: "0.1"
  - to: D-18
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

P-2-1〜P-2-4 の各検査子から受け取った全違反候補に対し、suppress（ノード単位抑制）・scheduled（フェーズ限定発火）・activate_stage（ステージ限定発火）・always_error（抑制不可 RULE）の各規則を適用して抑制済み RULE 違反リスト（D-6）を確定する。抑制ロジックの一元管理が単一責務であり、各検査子は「論理違反の検出」のみに集中できる。
**責務（単一動詞）**: 抑制・発火規則を違反候補に適用して D-6 を確定する
**提供価値**: suppress/scheduled/activate_stage の適用が P-2-1〜P-2-4 に重複コピーされていた横断関心事を 1 プロセスに集約し、抑制規則の変更箇所を単一化できる
**入力**:
- 各検査子（P-2-1-1/1-2/2-1〜4/3-1〜4/4-1〜3）から送出される違反候補（P-2 親経由）
- D-9（フェーズ・ステージ状態・current_phase/current_stage/phases/stages・P-5-3 が生成）を消費（P→D）
- D-12（always-error 規則・always_error セクション・P-5-3 が生成）を消費（P→D）
- D-14（ルール発火ステージ表・rule_activation・P-5-3 が生成）を消費（P→D）
- D-18（属性検査ビュー・suppress/scheduled スライスを含む・P-1-6 が生成）を消費（P→D）
**出力**: D-6（RULE 違反リスト・抑制適用済み）が P-2-5 に依存（D→P）、P-4 が消費
**トリガ**: E-1 に依存（P→E）

---

## P-3: カバレッジ点検

<details><summary>⬡ P-3 · v0.2.0</summary>

```yaml
id: P-3
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-14
    ref_version: "0.2"
  - to: FND-4
    ref_version: "0.1"
```
</details>

（P-3-1: グラフ網羅性・P-3-2: 仕様カバレッジ計測 に分担）カバレッジ点検を担う親プロセス。

---

### P-3-1: グラフ網羅性点検

<details><summary>⬡ P-3-1 · v0.2.0</summary>

```yaml
id: P-3-1
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-29
    ref_version: "0.1"
  - to: SPEC-30
    ref_version: "0.2"
  - to: D-20
    ref_version: "0.1"
  - to: D-10
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

（P-3-1-1: 未駆動出力検出・P-3-1-2: 未定義反応イベント検出・P-3-1-3: 未消費入力検出 に責務を委譲）分析層ノードの接続網羅性を確認する親プロセス。消費入力の明示は各子プロセスに移す。
**入力**: D-20（分析層トポロジビュー・P-1-6 が生成）・D-10（必須接続規則・P-5-3 が生成）を消費（P→D）
**トリガ**: E-1 に依存（P→E）

---

### P-3-1-1: 未駆動出力検出

<details><summary>⬡ P-3-1-1 · v0.1.0</summary>

```yaml
id: P-3-1-1
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-30-1
    ref_version: "0.1"
  - to: D-20
    ref_version: "0.1"
  - to: D-10
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

分析層トポロジビュー（D-20）から O→P 辺が 0 本の O ノードを検出する。
**責務（単一動詞）**: O ノードの生成元 P 依存辺（O→P）の欠如を検出する
**提供価値**: 価値経路の終端漏れ（出力が生成プロセスを持たない状態）を可視化し、設計の穴を早期発見できる
**入力**: D-20（分析層トポロジビュー・I/O/D/P/E ノードと辺の接続情報）・D-10（必須接続規則・must_link_to 等）を消費（P→D）
**出力**: 網羅性穴候補（O→P 欠如リスト）を生成（P-3-1 経由で P-3→P-4 へ）
**トリガ**: E-1 に依存（P→E）

---

### P-3-1-2: 未定義反応イベント検出

<details><summary>⬡ P-3-1-2 · v0.1.0</summary>

```yaml
id: P-3-1-2
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-30-2
    ref_version: "0.1"
  - to: D-20
    ref_version: "0.1"
  - to: D-10
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

分析層トポロジビュー（D-20）から P→E 辺の被依存が 0 本の E ノードを検出する。
**責務（単一動詞）**: E ノードへの P 依存辺（P→E）の欠如を検出する
**提供価値**: 反応が未定義のイベント（どのプロセスも依存していない事象）を可視化し、トリガ欠落を検出できる
**入力**: D-20（分析層トポロジビュー）・D-10（必須接続規則）を消費（P→D）
**出力**: 網羅性穴候補（E←P 欠如リスト）を生成（P-3-1 経由で P-3→P-4 へ）
**トリガ**: E-1 に依存（P→E）

---

### P-3-1-3: 未消費入力検出

<details><summary>⬡ P-3-1-3 · v0.1.0</summary>

```yaml
id: P-3-1-3
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-30-3
    ref_version: "0.1"
  - to: D-20
    ref_version: "0.1"
  - to: D-10
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

分析層トポロジビュー（D-20）から P→I 辺の被依存が 0 本の I ノードを検出する。
**責務（単一動詞）**: I ノードへの P 消費辺（P→I）の欠如を検出する
**提供価値**: 入力経路の起点漏れ（どのプロセスにも消費されない入力）を可視化し、価値経路の断絶を検出できる
**入力**: D-20（分析層トポロジビュー）・D-10（必須接続規則）を消費（P→D）
**出力**: 網羅性穴候補（I←P 欠如リスト）を生成（P-3-1 経由で P-3→P-4 へ）
**トリガ**: E-1 に依存（P→E）

---

### P-3-2: 仕様カバレッジ計測

<details><summary>⬡ P-3-2 · v0.2.0</summary>

```yaml
id: P-3-2
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-14
    ref_version: "0.2"
  - to: D-21
    ref_version: "0.1"
  - to: D-13
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

（P-3-2-1: FR×condition 充足集計・P-3-2-2: テーブル整形・FR-id 昇順出力 に責務を委譲）仕様カバレッジ計測を担う親プロセス。消費入力の明示は各子プロセスに移す。
**入力**: D-21（仕様カバレッジビュー・P-1-6 が生成）・D-13（condition 語彙・網羅規則・P-5-3 が生成）を消費（P→D）
**トリガ**: E-1 に依存（P→E）

---

### P-3-2-1: FR×condition 充足集計

<details><summary>⬡ P-3-2-1 · v0.1.0</summary>

```yaml
id: P-3-2-1
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-14-1-2
    ref_version: "0.1"
  - to: D-21
    ref_version: "0.1"
  - to: D-13
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

仕様カバレッジビュー（D-21）の FR ごとに condition 軸（normal/boundary/empty/failure/error）で SPEC と TD の充足状況を集計する。
**責務（単一動詞）**: FR×condition の充足マップを集計する
**提供価値**: カバレッジ事実の定量算出・FR ごとに何が揃い何が欠けているかを数値で把握できる
**入力**: D-21（仕様カバレッジビュー・FR/SPEC/TD と condition 属性・refines 辺を含む）・D-13（condition 語彙・網羅規則）を消費（P→D）
**出力**: FR×condition 充足マップ（P-3-2-2 へ渡す中間データ）を生成
**トリガ**: E-1 に依存（P→E）

---

### P-3-2-2: テーブル整形・FR-id 昇順出力

<details><summary>⬡ P-3-2-2 · v0.1.0</summary>

```yaml
id: P-3-2-2
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-14-1-1
    ref_version: "0.1"
  - to: SPEC-14-1-3
    ref_version: "0.1"
  - to: SPEC-14-1-4
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

P-3-2-1 が生成した FR×condition 充足マップをヘッダ付き・FR-id 昇順でカバレッジテーブルに整形する。
**責務（単一動詞）**: FR×condition 充足マップをカバレッジテーブル形式に整形・昇順出力する
**提供価値**: 可読なカバレッジテーブルとして D-7 素材を提供し、O-2 出力の土台となる
**入力**: FR×condition 充足マップ（P-3-2-1 の出力）を消費
**出力**: カバレッジテーブル（D-7 素材・P-3 経由で P-4 へ）・終了コード 0（SPEC-14-1-4）を生成
**トリガ**: E-1 に依存（P→E）

---

## P-4: レポート生成

<details><summary>⬡ P-4 · v0.2.0</summary>

```yaml
id: P-4
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-25
    ref_version: "0.2"
  - to: D-5
    ref_version: "0.1"
  - to: D-6
    ref_version: "0.1"
  - to: D-7
    ref_version: "0.1"
  - to: DD-7
    ref_version: "0.1"
```
</details>

（P-4-1: 違反レコード統合・P-4-2: 深刻度順整列・P-4-3: G 番号付与・整形・P-4-4: 終了コード決定 に責務を委譲）RULE 違反リストとカバレッジ計測結果をレポートとして出力する親プロセス。消費入力の明示は各子プロセスに移す。

---

### P-4-1: 違反レコード統合

<details><summary>⬡ P-4-1 · v0.1.0</summary>

```yaml
id: P-4-1
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-25
    ref_version: "0.2"
  - to: D-5
    ref_version: "0.1"
  - to: D-6
    ref_version: "0.1"
  - to: D-7
    ref_version: "0.1"
```
</details>

パース段違反（D-5）・RULE 違反（D-6）・カバレッジ計測結果（D-7）を 1 本の違反レコード列に合流させる。
**責務（単一動詞）**: D-5・D-6・D-7 の違反レコードを 1 列に統合する
**提供価値**: 下流の整列・整形が単一コレクションを対象にできる（単一レポート源の確立）
**入力**: D-5（パース段違反リスト）・D-6（RULE 違反リスト）・D-7（カバレッジ計測結果）を消費（P→D）
**出力**: 統合違反レコード列（P-4-2 へ渡す中間データ）を生成

---

### P-4-2: 深刻度順整列

<details><summary>⬡ P-4-2 · v0.1.0</summary>

```yaml
id: P-4-2
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-25-1
    ref_version: "0.1"
```
</details>

P-4-1 が生成した統合違反レコード列を ERROR→WARNING→INFO の深刻度順に整列する。
**責務（単一動詞）**: 統合違反レコード列を深刻度順に整列する
**提供価値**: 重要度可視化・レビュアーが重大な違反から順に確認できる
**入力**: 統合違反レコード列（P-4-1 の出力）を消費
**出力**: 整列済み違反列（P-4-3 へ）・ERROR 件数（P-4-4 へ）を生成

---

### P-4-3: G 番号付与・整形

<details><summary>⬡ P-4-3 · v0.1.0</summary>

```yaml
id: P-4-3
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-25
    ref_version: "0.2"
  - to: SPEC-14-1-1
    ref_version: "0.1"
```
</details>

整列済み違反列に G# 番号を採番し、O-1・O-2 の出力形式に整形する。
**責務（単一動詞）**: 整列済み違反列に G# 採番して O-1・O-2 形式に整形する
**提供価値**: 参照可能な指摘番号（G#）付きレポートの生成・レビュアーが指摘を番号で追跡できる
**入力**: 整列済み違反列（P-4-2 の出力）を消費
**出力**: O-1（RULE 違反レポート）・O-2（カバレッジ点検結果）が P-4-3（P-4 経由）に依存（O→P）

---

### P-4-4: 終了コード決定

<details><summary>⬡ P-4-4 · v0.2.0</summary>

```yaml
id: P-4-4
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-25-2
    ref_version: "0.1"
  - to: SPEC-25-3
    ref_version: "0.1"
  - to: FND-95
    ref_version: "0.2"
```
</details>

ERROR 件数が 1 以上であれば終了コード 1、0 件であれば終了コード 0 を決定する。
**責務（単一動詞）**: ERROR 件数を評価して終了コードを決定する
**提供価値**: CI ゲート実現・自動パイプラインが違反有無をコードで判定できる
**入力**: ERROR 件数（P-4-2 の出力）を消費
**出力**: O-6（終了コード 0 または 1）を生成——O-6 が生成元 P-4-4（本リーフ）に依存（O→P）

> **改訂理由（MINOR バンプ v0.1→v0.2）**:
> - 出力本文を「終了コード（0 または 1）を生成」から「**O-6（終了コード 0/1）を生成**」に更新し、終端出力が O ノードとして台帳に存在することを明示（PR6 価値経路の穴・FND-95 解消）。O-6 の生成元辺は本リーフ P-4-4 に張る（O→P）。
> - `→FND-95`（ref_version "0.2"）バックリファレンス辺を追加（FND-95 resolved 処置対象としての辺付与・FND-93/94 先例に倣う）。

---

## P-5: 設定ファイル読み込み

<details><summary>⬡ P-5 · v0.2.0</summary>

```yaml
id: P-5
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-21
    ref_version: "0.3"
  - to: I-5
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
  - to: DD-7
    ref_version: "0.1"
```
</details>

（P-5-1: config 読込 / P-5-2: スキーマ検証 / P-5-3: 設定スライス組立 に責務を委譲）config.yaml を読み込み、検証し、消費先ごとのフィールド単位スライス（D-9〜D-14・D-16）へ射影する親プロセス。消費入力（I-5）・トリガ（E-1）の明示は各子プロセスに移す。他プロセスは config.yaml を直接読まず P-5 が生成するスライスを経由する（FND-21）。
**トリガ**: E-1 に依存（P→E・P-1 と並行または先行して実行）

---

### P-5-1: config 読込

<details><summary>⬡ P-5-1 · v0.1.0</summary>

```yaml
id: P-5-1
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-21
    ref_version: "0.3"
  - to: I-5
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

config.yaml ファイルを UTF-8 で読み込み、生 config マップを生成する。
**責務（単一動詞）**: config.yaml を読み込む
**提供価値**: 設定の唯一の入口を確立し、他プロセスが直接ファイルを読む二重依存を防ぐ
**入力**: I-5（config.yaml）を消費（P→I）
**出力**: 生 config マップ（P-5-2 が消費する P-5 内部中間物）が生成される
**トリガ**: E-1 に依存（P→E）

---

### P-5-2: スキーマ検証

<details><summary>⬡ P-5-2 · v0.1.0</summary>

```yaml
id: P-5-2
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-21
    ref_version: "0.3"
  - to: E-1
    ref_version: "0.5"
```
</details>

P-5-1 が生成した生 config マップの必須キー・型を検証し、検証済み config マップを生成する。
**責務（単一動詞）**: config マップのスキーマを検証する
**提供価値**: 壊れた設定で後段プロセスを走らせないフェイルファストの保証
**入力**: 生 config マップ（P-5-1 が生成する P-5 内部中間物）を消費
**出力**: 検証済み config マップ（P-5-3 が消費する P-5 内部中間物）が生成される
**トリガ**: E-1 に依存（P→E）

---

### P-5-3: 設定スライス組立

<details><summary>⬡ P-5-3 · v0.1.0</summary>

```yaml
id: P-5-3
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-21
    ref_version: "0.3"
  - to: SPEC-24
    ref_version: "0.2"
  - to: E-1
    ref_version: "0.5"
```
</details>

検証済み config マップを消費先ごとのフィールド単位スライス（D-9〜D-14・D-16）へ射影・組立する。
**責務（単一動詞）**: config フィールドをスライスへ射影・組立する
**提供価値**: スタンプ結合の解消起点——消費先が必要なフィールド断片だけを受け取れるようにし、他フィールド変更の影響波及を防ぐ
**入力**: 検証済み config マップ（P-5-2 が生成する P-5 内部中間物）を消費
**出力**: D-9（フェーズ・ステージ状態）・D-10（必須接続規則）・D-11（決定スパイン規則）・D-12（always-error 規則）・D-13（condition 語彙・網羅規則）・D-14（ルール発火ステージ表）・D-16（走査スコープ設定）が生成元 P-5-3 に依存（D→P）
**トリガ**: E-1 に依存（P→E）

---

## P-6: in-graph 集合決定

<details><summary>⬡ P-6 · v0.2.0</summary>

```yaml
id: P-6
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-24
    ref_version: "0.2"
  - to: D-16
    ref_version: "0.1"
  - to: I-6
    ref_version: "0.3"
  - to: E-1
    ref_version: "0.5"
  - to: DD-7
    ref_version: "0.1"
  - to: FND-21
    ref_version: "0.1"
```
</details>

（P-6-1: include 一致抽出 / P-6-2: exclude 除外適用 に責務を委譲）D-16（走査スコープ設定・P-5-3 が生成）と I-6（ディレクトリ走査 .md ファイルパス一覧）から in-graph ファイル集合（D-1）を決定する親プロセス。消費入力の明示は各子プロセスに移す。config.yaml は P-5 経由（D-16）で受け取り直接読まない（FND-21）。旧 D-3 依存を D-16 に変更（スタンプ結合排除）。
**トリガ**: E-1 に依存（P→E・P-5 の直後）

---

### P-6-1: include 一致抽出

<details><summary>⬡ P-6-1 · v0.1.0</summary>

```yaml
id: P-6-1
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-24-1
    ref_version: "0.1"
  - to: I-6
    ref_version: "0.3"
  - to: D-16
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

I-6 の全 .md ファイルパスのうち D-16 の include glob に一致するものを抽出する。
**責務（単一動詞）**: include glob に一致するパスを抽出する
**提供価値**: 検証対象母集合の確定——include 条件に合わないファイルを後段へ渡さない
**入力**: I-6（ディレクトリ走査 .md ファイルパス一覧）・D-16（走査スコープ設定）を消費（P→I・P→D）
**出力**: include 一致パス集合（P-6-2 が消費する P-6 内部中間物）が生成される
**トリガ**: E-1 に依存（P→E）

---

### P-6-2: exclude 除外適用

<details><summary>⬡ P-6-2 · v0.1.0</summary>

```yaml
id: P-6-2
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-24-2
    ref_version: "0.1"
  - to: D-16
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
```
</details>

P-6-1 の include 一致集合から D-16 の exclude glob に一致するパスを除外し、D-1（in-graph ファイル集合）を確定する。
**責務（単一動詞）**: exclude glob に一致するパスを除外し D-1 を確定する
**提供価値**: out-of-graph ファイルの確実な排除（exclude 優先）——ダッシュボード・DFD 等が混入して誤検知が起きることを防ぐ
**入力**: include 一致パス集合（P-6-1 が生成する P-6 内部中間物）・D-16（走査スコープ設定）を消費（P→D）
**出力**: D-1（in-graph ファイル集合）が生成元 P-6 に依存（D→P）
**トリガ**: E-1 に依存（P→E）

---

## P-7: ノード著作・反映プロセス

<details><summary>⬡ P-7 · v0.4.0</summary>

```yaml
id: P-7
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-26
    ref_version: "0.3"
  - to: FND-10
    ref_version: "0.1"
  - to: FND-19
    ref_version: "0.1"
```
</details>

（P-7-1: 著作・P-7-2: 調停 に分担）ノードの著作から本ファイル反映までを担う親プロセス。著作エージェント・reconciliation エージェントはいずれも P-7 の内部定義（`.claude/agents/` の定義ファイル群）として組み込まれており、外部入力ではない。消費入力（I-7）・トリガ（E-2）の明示は各子プロセスに移す。

---

### P-7-1: 著作・tmp 出力

<details><summary>⬡ P-7-1 · v0.2.0</summary>

```yaml
id: P-7-1
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-38
    ref_version: "0.1"
  - to: SPEC-54
    ref_version: "0.1"
  - to: I-7
    ref_version: "0.1"
  - to: I-9
    ref_version: "0.1"
  - to: E-2
    ref_version: "0.3"
  - to: DD-7
    ref_version: "0.1"
  - to: FND-23
    ref_version: "0.1"
```
</details>

（P-7-1-1: テンプレート取得・P-7-1-2: 記載内容充填・P-7-1-3: 草案 tmp 書出 に責務を委譲）テンプレートと記載内容からノード草案を生成し tmp へ出力する親プロセス。消費入力の明示は各子プロセスに移す。テンプレート（I-7）だけでは中身が定まらず、記載内容（I-9）が揃って初めて草案を生成できる（SPEC-54・FND-23）。
**トリガ**: E-2 に依存（P→E・著作要求）

---

### P-7-1-1: テンプレート取得

<details><summary>⬡ P-7-1-1 · v0.1.0</summary>

```yaml
id: P-7-1-1
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-26-1
    ref_version: "0.1"
  - to: I-7
    ref_version: "0.1"
  - to: E-2
    ref_version: "0.3"
```
</details>

テンプレートファイル群（I-7）から著作対象の型に対応するテンプレート構造を取得する。
**責務（単一動詞）**: I-7 から型別テンプレート構造を取得する
**提供価値**: 規約準拠の雛形供給・後続の充填ステップが正しいフォーマットを前提にできる
**入力**: I-7（テンプレートファイル群）を消費（P→I）
**出力**: テンプレート構造（P-7-1-2 へ渡す中間データ）を生成
**トリガ**: E-2 に依存（P→E）

---

### P-7-1-2: 記載内容充填

<details><summary>⬡ P-7-1-2 · v0.1.0</summary>

```yaml
id: P-7-1-2
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-54-1
    ref_version: "0.1"
  - to: I-9
    ref_version: "0.1"
  - to: E-2
    ref_version: "0.3"
```
</details>

仕様著者（ACTOR-1）が提示した記載内容（I-9）をテンプレート構造の空欄に充填して著作対象ノードの本体を確定する。
**責務（単一動詞）**: I-9 をテンプレート構造に充填して充填済みノード本体を確定する
**提供価値**: 著作対象の確定（I-9 が揃って初めて草案が生成できる・SPEC-54）
**入力**: テンプレート構造（P-7-1-1 の出力）・I-9（ノード記載内容）を消費（P→I）
**出力**: 充填済みノード本体（P-7-1-3 へ渡す中間データ）を生成
**トリガ**: E-2 に依存（P→E）

---

### P-7-1-3: 草案 tmp 書出

<details><summary>⬡ P-7-1-3 · v0.1.0</summary>

```yaml
id: P-7-1-3
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-38-1
    ref_version: "0.1"
  - to: E-2
    ref_version: "0.3"
```
</details>

充填済みノード本体を `tmp/<sprint>/<parent-id>.md` に書き出してノード草案（D-8）を生成する。
**責務（単一動詞）**: 充填済みノード本体を tmp パスに書き出す
**提供価値**: 調停プロセス（P-7-2）への受け渡し物（D-8）を確定する
**入力**: 充填済みノード本体（P-7-1-2 の出力）を消費
**出力**: D-8（ノード草案・tmp）が P-7-1-3（P-7-1 経由）に依存（D→P）
**トリガ**: E-2 に依存（P→E）

---

### P-7-2: 調停・本ファイル反映

<details><summary>⬡ P-7-2 · v0.2.0</summary>

```yaml
id: P-7-2
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-39
    ref_version: "0.1"
  - to: D-8
    ref_version: "0.1"
  - to: E-2
    ref_version: "0.3"
  - to: DD-7
    ref_version: "0.1"
```
</details>

（P-7-2-1: 草案スキーマ検証・P-7-2-2: 本ファイル転記 に責務を委譲）ノード草案（D-8）を検証して本ファイルへ転記する親プロセス。消費入力の明示は各子プロセスに移す。
**入力**: D-8（ノード草案・tmp・P-7-1 が生成）を消費（P→D）
**トリガ**: E-2 に依存（P→E・P-7-1 完了後）

---

### P-7-2-1: 草案スキーマ検証

<details><summary>⬡ P-7-2-1 · v0.1.0</summary>

```yaml
id: P-7-2-1
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-39-1
    ref_version: "0.1"
  - to: SPEC-39-2
    ref_version: "0.1"
  - to: SPEC-39-3
    ref_version: "0.1"
  - to: D-8
    ref_version: "0.1"
  - to: E-2
    ref_version: "0.3"
```
</details>

P-7-1 が tmp に書き出したノード草案（D-8）の id 欠如・type 不正等を検証する。
**責務（単一動詞）**: D-8 のスキーマ適合性を検証する
**提供価値**: 壊れた草案の本ファイル混入防止・検証通過した草案だけが P-7-2-2 へ進む
**入力**: D-8（ノード草案・tmp）を消費（P→D）
**出力**: 検証済み草案（P-7-2-2 へ）または検証エラー（著作エラー報告）を生成
**トリガ**: E-2 に依存（P→E）

---

### P-7-2-2: 本ファイル転記

<details><summary>⬡ P-7-2-2 · v0.1.0</summary>

```yaml
id: P-7-2-2
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-38-2
    ref_version: "0.1"
  - to: E-2
    ref_version: "0.3"
```
</details>

P-7-2-1 が検証した草案を doc-system 本ファイルへ転記して著作済みノードファイル（O-3）を生成する。
**責務（単一動詞）**: 検証済み草案を本ファイルへ転記する
**提供価値**: 著作成果の確定・O-3（著作済みノードファイル）として仕様著者（ACTOR-1）が受け取れる状態になる
**入力**: 検証済み草案（P-7-2-1 の出力）を消費
**出力**: O-3（著作済みノードファイル）が P-7-2-2（P-7-2 経由）に依存（O→P）
**トリガ**: E-2 に依存（P→E）

---

## P-8: 依存グラフ出力処理

<details><summary>⬡ P-8 · v0.2.0</summary>

```yaml
id: P-8
type: P
labels: [post-mvp]
scheduled: "sprint-2"
edges:
  - to: SPEC-50
    ref_version: "0.2"
  - to: D-22
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
  - to: DD-6
    ref_version: "0.1"
```
</details>

グラフトポロジビュー（D-22）から依存グラフを構築し、指定フォーマット（dot または JSON 隣接リスト）で指定ファイルパスへ書き出す。フォーマット変換と書き出しという単一責務。
**入力**: D-22（グラフトポロジビュー・全ノード id・edges のみ・P-1-6 が生成）を消費（P→D）——旧 D-4 直読みからスタンプ結合解消済みスライスに変更
**出力**: O-4（依存グラフ出力ファイル）が P-8 に依存（O→P）——指定ファイルパスに dot/JSON ファイルを書き出す
**トリガ**: E-1 に依存（P→E・`--export-graph` オプション指定時のみ実行）

> **post-mvp 論理分解（PR8・印付きで保留）**：論理上はさらに〔グラフ構築〕〔フォーマット変換〕〔ファイル書出〕に割れる。MVP 外のため L2 分解は post-mvp 印で保留。

---

## P-9: 参照関係複雑度計算処理

<details><summary>⬡ P-9 · v0.2.0</summary>

```yaml
id: P-9
type: P
labels: [post-mvp]
scheduled: "sprint-2"
edges:
  - to: SPEC-51
    ref_version: "0.2"
  - to: D-22
    ref_version: "0.1"
  - to: D-15
    ref_version: "0.1"
  - to: E-1
    ref_version: "0.5"
  - to: DD-6
    ref_version: "0.1"
```
</details>

グラフトポロジビュー（D-22）から各ノードの in-degree・out-degree を算出し、ハブ閾値設定（D-15）によるハブ判定を行って複雑度メトリクスを id 昇順で stdout に出力する。メトリクス算出と整形出力という単一責務。
**入力**: D-22（グラフトポロジビュー・全ノード id・edges のみ・P-1-6 が生成）・D-15（ハブ閾値設定・P-5-3 が生成）を消費（P→D）——旧 D-4 直読みからスタンプ結合解消済みスライスに変更
**出力**: O-5（参照関係複雑度メトリクスレポート）が P-9 に依存（O→P）——stdout に行形式で出力する
**トリガ**: E-1 に依存（P→E・`--complexity` オプション指定時のみ実行）

> **post-mvp 論理分解（PR8・印付きで保留）**：論理上〔次数算出〕〔ハブ判定〕〔整形出力〕に割れる。post-mvp 印で保留。
