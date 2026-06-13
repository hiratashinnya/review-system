---
version: "0.1.0"
---
# データフロー図（DFD）

> 分析層ノード（ACTOR / I / O / D / P / E；`01-actors`・`02-io`・`03-processes`・`04-events`）から機械的に導出した DFD。
> E-1（点検フロー）・E-2（著作フロー）の 2 イベントを **Level 0**（コンテキスト）と **Level 1**（プロセス分解）で図示する。
> 本ファイルは **out-of-graph**（`trace_scope.exclude` 対象・ノードを持たない派生図）。
> 分析層ノードの版が上がったら本図を再生成すること。

---

## Level 0: コンテキスト図

外部アクタ・系入出力の全体像。

```mermaid
flowchart LR
  classDef actor fill:#dae8fc,stroke:#6c8ebf,color:#000
  classDef sys   fill:#d5e8d4,stroke:#82b366,color:#000
  classDef idata fill:#fff2cc,stroke:#d6b656,color:#000
  classDef odata fill:#f8cecc,stroke:#b85450,color:#000

  ACTOR1["仕様著者\n(ACTOR-1)"]:::actor
  ACTOR2["レビュアー\n(ACTOR-2)"]:::actor
  FS["OS ファイルシステム"]:::actor
  SYS(["spec-inspector"]):::sys

  ACTOR1 -->|"I-1 ノードファイル群"| SYS
  ACTOR1 -->|"I-7 テンプレートファイル群"| SYS
  FS      -->|"I-5 config.yaml"| SYS
  FS      -->|"I-6 .md パス一覧"| SYS
  SYS -->|"O-1 RULE 違反レポート"| ACTOR2
  SYS -->|"O-2 カバレッジ点検結果"| ACTOR2
  SYS -->|"O-3 著作済みノードファイル"| ACTOR1
```

---

## Level 1: E-1 点検フロー

E-1（点検要求）がトリガする処理チェーン全体。
前処理（P-5/P-6）→ パース（P-1）→ 検査（P-2-x / P-3-x）→ レポート（P-4）の 4 段。

```mermaid
flowchart TD
  classDef actor fill:#dae8fc,stroke:#6c8ebf,color:#000
  classDef proc  fill:#d5e8d4,stroke:#82b366,color:#000
  classDef idata fill:#fff2cc,stroke:#d6b656,color:#000
  classDef odata fill:#f8cecc,stroke:#b85450,color:#000
  classDef ddata fill:#e1d5e7,stroke:#9673a6,color:#000

  ACTOR1["仕様著者 / CI\n(ACTOR-1)"]:::actor

  subgraph inp["入力"]
    direction LR
    I1["I-1\nノードファイル群"]:::idata
    I5["I-5\nconfig.yaml"]:::idata
    I6["I-6\n.md パス一覧"]:::idata
    I2["I-2 suppress 設定\nI-3 scheduled 設定\nI-4 ref_version 値"]:::idata
  end

  subgraph pre["前処理（P-5 / P-6）"]
    P5["P-5\n設定ファイル読み込み"]:::proc
    P6["P-6\nin-graph 集合決定"]:::proc
    D1[["D-1\nin-graph ファイル集合"]]:::ddata
  end

  P1["P-1\nノード受付・パース\n(RULE-023〜028)"]:::proc

  subgraph rule["P-2 RULE 検査"]
    direction TB
    P21["P-2-1\nドリフト・義務辺検査"]:::proc
    P22["P-2-2\n構造完結性検査"]:::proc
    P23["P-2-3\nカバレッジ属性検査"]:::proc
    P24["P-2-4\n検証層完結性検査"]:::proc
  end

  subgraph cov["P-3 カバレッジ点検"]
    direction TB
    P31["P-3-1\nグラフ網羅性点検"]:::proc
    P32["P-3-2\n仕様カバレッジ計測"]:::proc
  end

  P4["P-4\nレポート生成\n(深刻度順・G# 番号付け)"]:::proc

  subgraph out["出力"]
    direction LR
    O1["O-1\nRULE 違反レポート"]:::odata
    O2["O-2\nカバレッジ点検結果"]:::odata
    ACTOR2["レビュアー\n(ACTOR-2)"]:::actor
  end

  ACTOR1 -->|"E-1 点検要求"| pre

  I5 --> P5
  I5 --> P6
  I6 --> P6
  P6 --> D1

  I1 --> P1
  D1 --> P1
  P5 -->|"設定オブジェクト"| P1
  P5 -.->|"設定（共有）"| rule
  P5 -.->|"設定（共有）"| cov

  P1 -->|"構造化ノードセット"| rule
  P1 -->|"構造化ノードセット"| cov
  P1 -->|"パース段違反リスト"| P4

  I2 -.->|"suppress / scheduled\n/ ref_version"| rule

  rule -->|"RULE 違反リスト群"| P4
  cov  -->|"カバレッジ計測結果"| P4

  P4 --> O1
  P4 --> O2
  O1 --> ACTOR2
  O2 --> ACTOR2
```

> **注**: I-2（suppress）・I-3（scheduled）・I-4（ref_version）は I-1 ノードファイルのフィールドとして埋め込まれており、
> P-1 のパース後に各 P-2-x が個別に参照する（P-2-1 は I-4、P-2-2/2-3/2-4 は I-2/I-3）。
> 点線矢印は共有参照を示す（データコピーではない）。

---

## Level 1: E-2 著作フロー

E-2（著作要求）がトリガする処理チェーン。
著作（P-7-1）→ 調停（P-7-2）の 2 段。

```mermaid
flowchart LR
  classDef actor fill:#dae8fc,stroke:#6c8ebf,color:#000
  classDef proc  fill:#d5e8d4,stroke:#82b366,color:#000
  classDef idata fill:#fff2cc,stroke:#d6b656,color:#000
  classDef odata fill:#f8cecc,stroke:#b85450,color:#000

  ACTOR1["仕様著者\n(ACTOR-1)"]:::actor
  I7["I-7\nテンプレートファイル群"]:::idata
  P71["P-7-1\n著作・tmp 出力"]:::proc
  P72["P-7-2\n調停・本ファイル反映"]:::proc
  O3["O-3\n著作済みノードファイル"]:::odata

  ACTOR1 -->|"E-2 著作要求"| P71
  I7      --> P71
  P71     -->|"tmp 草案"| P72
  P72     --> O3
  O3      -->|"著作成果物"| ACTOR1
```

---

## データフロー一覧

### 入力（I）・内部データ（D）

| ID | 内容 | 発生源 | 消費先 |
|---|---|---|---|
| I-1 | ノードファイル群（.md + YAML フロントマター） | ACTOR-1 | P-1 |
| I-2 | suppress 設定（ノード内フィールド） | ACTOR-1（ノード著作時） | P-2-2 / P-2-3 / P-2-4 |
| I-3 | scheduled 設定（ノード内フィールド） | ACTOR-1（ノード著作時） | P-2-2 / P-2-3 / P-2-4 |
| I-4 | ref_version 値（辺内フィールド） | ACTOR-1（辺定義時） | P-2-1 |
| I-5 | config.yaml（current_stage・must_link_to・trace_scope 等） | OS/FS | P-5 / P-6 |
| I-6 | ディレクトリ走査 .md ファイルパス一覧 | OS/FS | P-6 |
| I-7 | 型別著作テンプレートファイル群 | OS/FS（リポジトリ管理） | P-7-1 |
| D-1 | in-graph ファイル集合（trace_scope フィルタ適用後） | P-6 | P-1 |

### 出力（O）

| ID | 内容 | 生成元 | 受け手 |
|---|---|---|---|
| O-1 | RULE 違反レポート（G# 番号・ノード ID・RULE 番号・メッセージ） | P-4 | ACTOR-2 |
| O-2 | カバレッジ点検結果（孤立ノード・未駆動出力・未定義反応一覧） | P-4 | ACTOR-2 |
| O-3 | 著作済みノードファイル（doc-system 記法準拠 .md） | P-7-2 | ACTOR-1 |

### プロセス概要（P）

| ID | 責務 | 主な入力 | 主な出力 |
|---|---|---|---|
| P-5 | 設定ファイル読み込み | I-5 | 検証済み設定オブジェクト → P-1/P-2/P-3 |
| P-6 | in-graph 集合決定（trace_scope フィルタ） | I-5, I-6 | D-1 |
| P-1 | ノード受付・パース（RULE-023〜028） | I-1, D-1, 設定 | 構造化ノードセット・パース段違反リスト |
| P-2-1 | ドリフト・義務辺検査（RULE-001/002/004/022） | 構造化ノードセット, I-4 | ドリフト違反リスト |
| P-2-2 | 構造完結性検査（RULE-005〜008） | 構造化ノードセット, I-2, I-3 | 構造違反リスト |
| P-2-3 | カバレッジ属性検査（RULE-016〜019） | 構造化ノードセット, I-2, I-3 | カバレッジ属性違反リスト |
| P-2-4 | 検証層完結性検査（RULE-006 verification / 020/021） | 構造化ノードセット, I-2, I-3 | 検証層違反リスト |
| P-3-1 | グラフ網羅性点検（未駆動出力・未定義反応） | 構造化ノードセット | グラフ網羅性穴リスト |
| P-3-2 | 仕様カバレッジ計測（condition 軸集計） | 構造化ノードセット | カバレッジテーブル |
| P-4 | レポート生成（深刻度順整列・G# 番号付け・終了コード） | 全違反リスト・計測結果 | O-1, O-2 |
| P-7-1 | 著作・tmp 出力 | I-7（テンプレート） | tmp 草案 |
| P-7-2 | 調停・本ファイル反映 | tmp 草案 | O-3 |
