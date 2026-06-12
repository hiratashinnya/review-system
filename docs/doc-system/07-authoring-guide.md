---
version: "0.1.1"
---
# ドキュメント・オーサリングガイド

> このガイドはドキュメントシステムでノードを書くときの**完全な実践リファレンス**（共通手順・型別本文フォーマット・RULE 受け入れ条件・suppress・辺方向）。
> スキーマ定義 → [02-meta-schema.md](02-meta-schema.md)、接続要否 → [03-connection-matrix.md](03-connection-matrix.md)、テンプレート → `templates/`。
>
> **型別の著作規約は型別著作エージェントが持つ**（旧 doc-authoring SKILL は廃止＝畳み込み）：
> VAL/SR/FR/NFR→`requirements-author`・SPEC→`spec-author`・ACTOR/I/O/D/P/E→`analysis-author`・
> ORC/DS/MOD/DM/PORT/PRS/SCM/CFG/PROMPT/TERM→`design-author`・TD/TC/TR/VERIFY/FND/DD/Q/PEND→`verification-author`・
> 整合確認・本ファイル確定→`reconciliation`。
> **このガイドは横断的な実践リファレンス**（DD/Q の運用は [CLAUDE.md](../../CLAUDE.md)、点検は spec-inspector）。
>
> **エッジは無名依存辺**（kind/status 廃止・DD-012/013）：`- to: X` ＋ `ref_version` のみ。`A→B`＝A は B に依存。

---

## 1. ノード作成の基本手順

```
1. テンプレを選ぶ   → docs/doc-system/templates/<layer>/<type>.md
2. id を採番する    → PREFIX-N（連番・永続。意味は heading が持つ）
3. type を設定する  → 02-meta-schema §6 の型値から
4. 必須 edges を書く → 03-connection-matrix ✅ の辺は必須（RULE-006）
5. condition を書く → SPEC・TD には必須（RULE-016）
6. 本文を書く       → 型ごとのフォーマット（§3 参照）
7. RULE を確認する  → §4 受け入れ条件チェックリスト
```

### ファイル配置

| 層 | ファイル |
|---|---|
| Why | `why/val.md`, `why/sr.md` |
| What | `what/fr.md`, `what/spec.md`, `what/nfr.md` |
| 共有語彙 | `shared/terms.md` |
| 分析 | `analysis/context.md`, `analysis/dfd.md`, `analysis/events.md` |
| 設計・振る舞い | `design-behavior/orchestration.md`, `design-behavior/state.md` |
| 設計・静的 | `design-static/modules.md`, `design-static/types.md`, `design-static/prompts.md` 等 |
| 検証 | `verification/test-design.md`, `verification/tests.md`, `verification/test-result.md` 等 |

---

## 2. メタ属性の書き方

### 全ノード共通

```yaml
id: FR-001          # PREFIX-N。採番したら変えない（意味変化はリネームしない）
type: FR            # 型値（§6）
labels: []          # 任意の分類タグ（post-mvp, experimental 等）
scheduled: ""       # 対応予定フェーズ（後フェーズなら全ルールがサイレント）
suppress: []        # ルール抑制リスト。理由 comment 必須。RULE-007 は抑制不可
```

### SPEC・TD のみ

```yaml
condition: normal   # normal | boundary | failure | error
                    # TD の condition は verifies 先 SPEC の condition と一致させる（RULE-019）
```

### TR のみ

```yaml
result: PASS        # PASS | FAIL（なしは RULE-020 ERROR・ボディに書かない）
log_ref: "ci/..."   # ログのパス/URL（PASS/FAIL 問わず必須・なしは RULE-021 ERROR）
```

### suppress の書き方

```yaml
suppress: [RULE-018]   # error path なし: 外部 API は常時稼働前提（SLA 99.99%）
```

理由のない suppress はレビューで拒否（always_error の RULE-007 は suppress 不可）。

---

## 3. ノード型別・本文フォーマット

### Why 層

**VAL（価値命題）**
```
[誰に] [何の便益をもたらすか] を1文で記述。
```

**SR（ステークホルダー要求）**
```
[ステークホルダー] が [状況] において [欲求・期待] を持つ。
```

### What 層

**FR（機能要求）**
```
[システムが持つべき機能・ユーザー価値を1文で記述]
```
> FR は「なぜこの機能が必要か」粒度。テスタブル条件は SPEC に分割する（USDM 分割）。

**SPEC（機能仕様）**
```
**前提条件**: [正常に動く前提・文脈]
**入力/トリガ**: [有効な入力・操作]
**期待動作**: [正常応答・状態変化]
**例**: input X → expected output Y  （具体値必須。プレースホルダ禁止）
```
condition ごとにフォーマットが変わる（normal/boundary/empty/failure/error → templates/what/spec.md 参照）。

#### SPEC テスタビリティ基準（必須チェックリスト）

SPEC 本文は「2人の異なる実装者が同じ本文を読んで同一のテストを書ける」レベルの一意性を持つこと。
以下をすべて満たさない SPEC は受け入れ条件不通過（reconciliation 差し戻し）。

- [ ] **前提条件が定量的**：ノード数・ファイル数・フィールド値を具体的に示す。「いくつかのノード」「適切な設定」禁止。
- [ ] **入力/トリガが一意**：同じ入力を2人が読んで同じテストデータを作れる。コマンド例・ファイル内容例を記載。
- [ ] **出力フォーマットが明記**：「報告する」禁止。`{SEVERITY}|{file}:{line}|{RULE-NNN}|{node-id}|{message}` のような具体的行形式を示す。
- [ ] **終了コードが明記**：condition: failure/error/empty の SPEC は期待する終了コード（0 or 1）を示す。
- [ ] **全順序が定まる**：複数出力行がある場合、曖昧なく順序が定まるソートキーをすべて列挙する。
- [ ] **具体例が1つ以上**：`例: input_A → output_B` の形式で実値を記載（プレースホルダ `[xxx]` 禁止）。
- [ ] **曖昧語を使わない**：「適切な」「正しく」「relevant な」「基本的に」禁止。すべて定量・定義で置き換える。
- [ ] **condition: empty を正しく使う**：空入力・ゼロ件・null・未設定ケースは必ず `condition: empty` で独立 SPEC 化する（boundary や failure に混入させない）。

**NFR（非機能・制約）**
```
[制約の内容：性能・技術選択・安全デフォルト等]
```

### 分析層

**ACTOR（外部アクタ）**
```
[外部エンティティの役割・範囲]
```

**I（入力）**
```
**もの**: [入力の実体]
**発生源**: [どのアクタから発生するか]
**形式**: [型・フォーマット]
**タイミング**: [いつ・どのトリガで]
```

**O（出力）**
```
**もの**: [出力の実体]
**受け手**: [どのアクタが受け取るか]
**形式**: [型・フォーマット]
```

**D（内部データフロー）**
```
**もの**: [プロセス間で受け渡す内部データの実体（系外に出ない）]
**形式**: [型・フォーマット]
```
> 系外アクタとやり取りする入出力は I/O、プロセス間だけの中間データは D。

**P（論理プロセス）**
```
[単一責務を1文で記述（〜を〜する）]
**入力**: I-xxx / D-xxx を消費（P の edges に `- to: I-xxx`）
**出力**: O-xxx / D-xxx が生成元として P に依存（O/D 側に `- to: P-xxx`）
**トリガ**: E-xxx に依存（P の edges に `- to: E-xxx`）
```

**E（イベント）**
```
**イベント名**: [イベントの短い名前]
**スティミュラス**: [刺激元アクタ（E の edges に `- to: ACTOR-xxx` 必須・DD-020）からの入力・刺激]
**アクション**: [システムが行う処理・行動（各 P が P→E でこの事象に依存）]
**レスポンス**: [生成される出力（O-# または自由記述）]
**アフェクト**: [このイベントが生む価値・便益]
```

### 設計層

**ORC（オーケストレーション段）**
```
**段の目的**: [この段が達成する結果（Result 型を返す）]
**入力**: [前段からの入力]
**出力**: [次段への出力または最終出力]
**失敗時**: [fail-close の振る舞い]
```

**DS（データストア）**
```
**保存対象**: [何を持つか]
**保存理由**: [なぜ持つか・どこで参照されるか]
**ライフサイクル**: [作成・更新・削除のタイミング]
```

**MOD（モジュール）**
```
[モジュールの責務を1文で記述]
**公開 I/F**: [公開する主要な関数・クラス]
**依存**: [依存するポート・モジュール]
```

**DM（ドメイン型）**
```
[型の目的・不変条件]
**フィールド**: [主要フィールドと型]
**制約**: [バリデーション・不変条件]
```

**PROMPT（プロンプトテンプレート）**
```
**役割**: [LLM に担わせる役割]
**入力変数**: [テンプレート変数一覧]
**出力形式**: [期待する出力の形式・スキーマ]
**注意事項**: [プロンプトインジェクション対策・制約]
```

### 検証層

**TD（テスト設計）**
```
**テスト観点**: [何を確認するか（正常動作 / 境界値 / 拒否 / フェイルセーフ）]
**前提条件**: [テスト実行前に揃えるべき状態]
**入力**: [テストデータ・操作手順]
**期待結果**: [合格条件（出力値・状態変化・ログ等）]
```

**TR（テスト結果）**
```
**実施日**: [YYYY-MM-DD]
**コミット ID**: [ハッシュ]
**テストケースバージョン**: [TD 側 ref_version]

<!-- FAIL の場合のみ -->
**根本原因**: [何が原因か]
**対処**: [どう修正したか / wontfix の場合その理由]
```
> `result` と `log_ref` は YAML メタに書く（ボディに書かない）。

**VERIFY（ドキュメント検証）**
```
**検証範囲**: [対象ドキュメント・要素]
**手法**: [レビュー・ウォークスルー・ツール確認等]
**実施日**: [YYYY-MM-DD]
**結果**: [問題なし / 指摘あり（→ FND-xxx 参照）]
```

**FND（指摘）**
```
**深刻度**: [ERROR / WARNING / INFO]
**内容**: [指摘の詳細]
**対応状況**: [open / resolved / wontfix]
**対応内容**: [どう直したか・直さない理由]
```

> **FND 解消時の必須操作**: 対応状況を `resolved` にする場合、**処置対象ノード側に `→ FND-x` の依存辺を追加する**（`ref_version` 必須）。
> これはバックリファレンス辺として永続記録になる。処置対象が削除された場合は FND 本文に「削除済みのため付与先なし」と明記すれば OK。
> reconciliation がこの辺の存在を確認するため、付与せずに resolved にすると **差し戻し**になる。

### 横断スパイン

**DD（意思決定）**
```
**論点**: [決定が必要な問い]
**選択肢**: [A. xxx / B. xxx / C. xxx]
**推奨**: [推奨案とその根拠]
**決定**: [採用した案]
**影響範囲**: [この決定が変える設計・実装の範囲]

**status: decided**
```

**Q（未決論点）**
```
**論点**: [未決の問い]
**選択肢**: [A. xxx / B. xxx]
**推奨**: [推奨案（オーナー判断前に必ず提示）]

**status: open**
```

---

## 4. 受け入れ条件（RULE パスチェックリスト）

ノードを書いたら以下を確認する。

### 全ノード共通

- [ ] `id` が一意（既存 ID と衝突なし）
- [ ] `type` が §6 の型値と一致
- [ ] `edges` の `to` がすべて実在する ID（RULE-007: always_error）
- [ ] 必須依存辺（config `must_link_to`/`must_be_linked_from`）が存在（RULE-006）
- [ ] 辺に `kind`/`status` がない・`to` は単数（リスト禁止）
- [ ] 完全孤立していない（RULE-005: always_error）
- [ ] `ref_version` が全辺にあり参照先の現在 `x.y` と一致（RULE-004）

### SPEC

- [ ] `condition` 属性あり（RULE-016 ERROR）
- [ ] TD から被依存（`must_be_linked_from: SPEC ← [TD]`・verification 発火）

### FR

- [ ] `condition: normal` の SPEC が少なくとも 1 本（RULE-017）
- [ ] `condition: failure` / `error` がなければ suppress 確認（RULE-018 WARNING）

### TD

- [ ] `condition` 属性あり（RULE-016 ERROR）
- [ ] 依存先 SPEC の `condition` と一致（RULE-019）

### TC

- [ ] TD への依存辺がある（`must_link_to: TC→TD`・RULE-006）

### TR

- [ ] `result: PASS|FAIL` が YAML メタにある（RULE-020 ERROR）
- [ ] `log_ref` がある（PASS/FAIL 問わず・RULE-021 ERROR）

### FND

- [ ] 対象要素への依存辺がある（`must_link_to: FND→any`・RULE-006）
- [ ] **対応状況が `resolved` の場合**: 処置対象ノードに `→ FND-x` 辺が付与されているか（処置対象削除時は FND 本文に「削除済みのため付与先なし」と明記）

### VERIFY

- [ ] 対象要素への依存辺がある（`must_link_to: VERIFY→any`・RULE-006）

### NFR

- [ ] FND/TC/VERIFY から被依存（`must_be_linked_from: NFR ← [FND,TC,VERIFY]`・verification 発火）

### DD / Q / PEND

- [ ] 義務辺が未反映のまま放置されていない（反映後は辺を削除し `X→DD` を張る・RULE-001/002/022）

---

## 5. suppress が必要なケース

| 状況 | suppress 対象 | 記述例 |
|---|---|---|
| FR に error path を作る設計意図がない | RULE-018 | `suppress: [RULE-018]  # error path なし: 外部 API は SLA 99.99% で常時稼働前提` |

suppress を付ける前に「本当に回避できないか」を確認する。suppress の多用は品質低下の兆候。
（検証層の必須接続はステージ発火で自動沈黙するため suppress 不要。）

---

## 6. エッジ方向の注意点（依存方向に統一・DD-017）

辺は無名依存辺。`A→B`＝「A は B に依存する（B が変われば A を見直す）」。

```
FR   → SR      ← FR が SR を精緻化（FR は SR に依存）
SPEC → FR      ← SPEC が FR を精緻化
TD   → SPEC    ← TD が SPEC を検証
TC   → TD      ← TC が TD を実現
TR   → TC      ← TR が TC の実行から生成

P → I          ← プロセスは消費する入力に依存（旧 consumes）
O → P          ← 出力は生成プロセスに依存（旧 produces を反転）
P → E          ← プロセスはトリガ事象に依存（旧 triggers を反転）
O → ACTOR      ← 出力は受け手アクタに依存
E → ACTOR      ← 事象は刺激元アクタに依存（必須・DD-020）
D → P          ← 内部データは生成プロセスに依存
CFG → SCM      ← 設定はスキーマに依存（旧 instantiates）
ORC → PROMPT   ← オーケストレーションはプロンプトに依存（旧 uses・任意）

廃止: see-also / replaces / extends / contradicts / decomposes（DD-014）
  矛盾は FND（FND→A・FND→B の2辺）・階層は ID パターン X-N から推論
```
