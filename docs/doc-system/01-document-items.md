# 文書項目セット

> 上流層を詳細化する連鎖（V字左腕）。各層の要素が 1 ノード。
> ノードは `id` を持ち、エッジ（上流参照辺）に **関係種別＋伝播ステータス＋参照版** を付与する。
> メタ属性スキーマの詳細は [02](02-meta-schema.md)、接続要否は [03](03-connection-matrix.md)。

---

## 層構成と要素型

### Why 層（なぜ作るか）

| 要素型 | ID プレフィックス | 1 ノードの単位 | 上流参照 | 必須リンク |
|---|---|---|---|---|
| 価値命題 | `VAL-` | 1 つの価値（誰に・何の便益） | なし（根） | 下流から ✅ 必須 |
| ステークホルダー要求 | `SR-` | 1 つの欲求・期待 | → `VAL-` | ✅ 必須 |

> ファイル：`why/val.md`・`why/sr.md`（別ファイル）

---

### What 層（何を満たすか）

| 要素型 | ID プレフィックス | 1 ノードの単位 | 上流参照 | 必須リンク |
|---|---|---|---|---|
| 機能要求 | `FR-` | 1 機能要求（システムが持つべき機能・ユーザー価値） | → `SR-`（直接） | ✅ 必須 |
| 機能仕様 | `SPEC-` | 1 テスト可能な仕様条件（入力・前提・期待動作を特定）。`condition` 属性で条件分類（normal/boundary/empty/failure/error） | → `FR-`（直接） | ✅ 必須。下流から TD が必須（must_be_linked_from・verification 発火）。condition 必須（RULE-016 ERROR） |
| 非機能/制約 | `NFR-` | 1 制約（性能・技術選択・安全側デフォルト等） | → `SR-`（直接） | 検証結果からリンク必須（§11） |

> ファイル：`what/fr.md`・`what/spec.md`・`what/nfr.md`（別ファイル）
> **USDM 分割**：FR は「なぜこの機能が必要か」（要求粒度）、SPEC は「どういう条件を満たすか」（仕様粒度・テスタブル）。

---

### 共有語彙（横断）

| 要素型 | ID プレフィックス | 1 ノードの単位 | 上流参照 |
|---|---|---|---|
| 用語／データ辞書 | `TERM-` | 1 用語（定義・型・制約） | → `SPEC-`（直接） |

> ファイル：`shared/terms.md`

---

### 分析層（要求 → 構造化）

| 要素型 | ID プレフィックス | 1 ノードの単位 | 上流参照 | 必須リンク |
|---|---|---|---|---|
| 外部アクタ | `ACTOR-` | 1 外部エンティティ | → `SR-` | ✅ E/I/O から被依存（参加） |
| 入力 | `I-` | 1 入力（もの＋発生源・系外発） | → `SPEC-` | ✅ P から被依存（P→I） |
| 出力 | `O-` | 1 出力（もの＋受け手・系外宛） | → `SPEC-`・`P-`（生成元）・`ACTOR-`（受け手） | ✅ O→P・O→ACTOR |
| 内部データ | `D-` | 1 内部データフロー（系外に出ない） | → `SPEC-`・`P-`（生成元） | ✅ P から被依存（P→D） |
| 論理プロセス | `P-` | 1 責務（単一責務まで分解） | → `SPEC-`（・I/D 消費・E トリガ） | ✅ SPEC 必須 |
| イベント | `E-` | 1 外部トリガ→反応ペア | → `SPEC-`・`ACTOR-`（刺激元） | ✅ E→ACTOR・P から被依存 |

> ファイル：`analysis/context.md`・`analysis/dfd.md`・`analysis/events.md`
> **階層 ID 対応**：`I-1` を分割すると `I-1-1`・`I-1-2` になる。親は `decomposes` 辺で子を指す。

---

### 設計層・振る舞い（どう動くか）

| 要素型 | ID プレフィックス | 1 ノードの単位 | 上流参照 |
|---|---|---|---|
| オーケストレーション段 | `ORC-` | 1 実行段（Result 返し） | → `E-` |
| 状態/データストア | `DS-` | 1 状態（何を・なぜ持つ） | → `P-` |

> ファイル：`design-behavior/orchestration.md`・`design-behavior/state.md`

---

### 設計層・静的（どう組むか）

| 要素型 | ID プレフィックス | 1 ノードの単位 | 上流参照 |
|---|---|---|---|
| モジュール | `MOD-` | 1 パッケージ/モジュール | → `P-` または → `D-` |
| ドメイン型 | `DM-` | 1 型（class/enum/値オブジェクト） | → `TERM-`, `MOD-` |
| ポート/アダプタ | `PORT-` | 1 抽象ポート or アダプタ | → `MOD-` |
| 永続設計 | `PRS-` | 1 保存形式/リポジトリ port | → `DS-` |
| スキーマ | `SCM-` | 1 外部ファイルスキーマ | → `SPEC-` |
| コンフィグ | `CFG-` | 1 設定項目/設定ファイル | → `SCM-`・`SPEC-` |
| プロンプトテンプレート | `PROMPT-` | 1 プロンプト雛形 | → `SPEC-` |

> ファイル：`design-static/modules.md`・`design-static/types.md`・`design-static/prompts.md` 等

---

### 実装層

| 要素型 | ID プレフィックス | 1 ノードの単位 | 上流参照 |
|---|---|---|---|
| ソース（docstring） | ソースファイル内 `@id` | 1 クラス / 公開関数 | → `DM-`・`PORT-`・`ORC-`（直接先のみ） |

> SRC は直接先（DM/PORT/ORC）のみ（D2 と同規則・D3）。

---

### 検証層

| 要素型 | ID プレフィックス | 1 ノードの単位 | 上流参照 | 必須リンク |
|---|---|---|---|---|
| テスト設計 | `TD-` | 1 テストシナリオ（設計）。`condition` は verifies 先 SPEC と一致させる | → `SPEC-` | ✅ SPEC を verifies（RULE-015 の対象辺）。condition 必須（RULE-016）。SPEC と一致（RULE-019） |
| テストコード | `TC-` | 1 テスト実装（テストケースのコード） | → `TD-` | ✅ TD を realizes |
| テスト結果 | `TR-` | 1 実行記録（`result: PASS/FAIL`・`log_ref`・実施日） | → `TC-` | `produced-by` 辺で TC に紐づける。RULE-020: result 必須。RULE-021: FAIL 時 log_ref 必須 |
| ドキュメント検証 | `VERIFY-` | 1 検証実施（範囲・手法・実施日） | → 対象文書要素 | ✅ verifies 辺が必須（RULE-013） |
| 指摘（finding） | `FND-` | 1 検証指摘（内容・深刻度・状態） | → 指摘対象要素、→ `NFR-`（validates） | ✅ found-in 辺が必須（RULE-009） |

> **テスト3層の役割分担**
> - `TD`: 何をどう確認するか（設計）。`SPEC → TD (verifies)` 辺がカバレッジの証跡。
> - `TC`: TD を実コードで実現（ユニットテスト等）。`TD → TC (realizes)`。
> - `TR`: TC の実行記録（コミット ID・合否・ログリンク）。`TC → TR (produced-by)`。
>
> `VERIFY` はドキュメント向け（コード不要の手動確認等）。`FND` は TC/VERIFY どちらから発生してもよく、NFR の検証証跡として機能する（§11）。

---

### 横断スパイン（意思決定・未決・先送り）

| 要素型 | ID プレフィックス | ライフサイクル（本文に記載） |
|---|---|---|
| 意思決定 | `DD-` | open → decided → closed |
| 未決論点 | `Q-` | open → deferred / decided → closed |
| 先送り | `PEND-` | deferred → open（再開）/ closed |

> **id は通貫**。ライフサイクルは本文（見出しや status バッジ）に記載。メタ属性には持たない。
> DD/Q/PEND の**義務辺の存在**がドリフト検出の核心（反映後は辺を削除し `X→DD` を張る・DD-016）。

---

## エッジ＝無名依存辺（詳細は [02 §5](02-meta-schema.md)）

辺に種別（kind）は持たない（DD-012）。`A → B` ＝「A は B に依存する（B が変われば A を見直す）」。
関係の名称は `(source 型, target 型)` から読み取る。下表は**依存辺が表す関係の読み**（参考）。

| 型ペア（source→target） | 読み | 方向の注意 |
|---|---|---|
| FR→SR, SPEC→FR, I/O/P/E→SPEC 等 | 詳細化（旧 refines） | 下流→上流 |
| SRC→DM/PORT/ORC | 実現（旧 realizes） | |
| CFG→SCM | 具体化（旧 instantiates） | |
| O→P | 出力は生成プロセスに依存（旧 produces 反転） | **依存方向に統一** |
| P→I, P→D | プロセスは消費入力に依存（旧 consumes） | |
| P→E | プロセスはトリガ事象に依存（旧 triggers 反転） | |
| O→ACTOR, E→ACTOR | 受け手/刺激元アクタに依存 | |
| TD→SPEC, VERIFY→任意 | 検証（旧 verifies） | |
| FND→NFR, TR→TC | 証跡（旧 validates/produced-by） | |
| DD/Q/PEND→任意 | 義務辺（反映追跡・唯一の逆向き） | source 型で識別 |

> **廃止**：`see-also`・`replaces`・`extends`・`contradicts`・`decomposes`（DD-014）。
> see-also＝参照は依存・replaces＝本文更新＋版・extends＝無名依存辺・contradicts＝FND・decomposes＝ID パターン。
