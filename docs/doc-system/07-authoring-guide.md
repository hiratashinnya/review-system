---
version: "0.1.0"
---
# ドキュメント・オーサリングガイド

> このガイドはドキュメントシステムでノードを書くときの実践的なリファレンス。
> スキーマ定義 → [02-meta-schema.md](02-meta-schema.md)、接続要否 → [03-connection-matrix.md](03-connection-matrix.md)、
> テンプレート → `templates/`。（旧 doc-authoring SKILL は廃止、authoring 規約は各フェーズスキルへ委譲）

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
result: PASS        # PASS | FAIL（機械チェック対象・ボディに書かない）
log_ref: ""         # ログのパス/URL（result: FAIL 時は必須）
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
```
condition ごとにフォーマットが変わる（normal/boundary/failure/error → templates/what/spec.md 参照）。

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

**P（論理プロセス）**
```
[単一責務を1文で記述（〜を〜する）]
**入力**: I-xxx を消費（consumes）
**出力**: O-xxx を生成（produces）
**トリガ**: E-xxx から起動（triggers）
```

**E（イベント）**
```
**トリガ**: [外部トリガの内容]
**反応**: [システムの反応]
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
**内容**: [指摘の詳細]
**深刻度**: [critical / major / minor / info]
**状態**: [open / resolved / wontfix]
**対象**: [found-in 辺で参照している要素]
```

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
- [ ] 接続マトリクス ✅ の辺がすべて存在（RULE-006）
- [ ] `see-also` 辺の `status` が `n/a`（RULE-014）
- [ ] `ref_version` が参照先の現在 `x.y` と一致（RULE-003/004）

### SPEC

- [ ] `condition` 属性あり（RULE-016）
- [ ] TD からの `verifies` 辺が存在（RULE-015）

### FR

- [ ] `condition: normal` の SPEC が少なくとも 1 本（RULE-017）
- [ ] `condition: failure` / `error` がなければ suppress か INFO 確認（RULE-018）

### TD

- [ ] `condition` 属性あり（RULE-016）
- [ ] `verifies` 先 SPEC の `condition` と一致（RULE-019）

### TC

- [ ] `realizes` 辺で TD に紐づいている（RULE-012: ERROR）

### TR

- [ ] `result: PASS|FAIL` が YAML メタにある（RULE-020）
- [ ] `result: FAIL` のとき `log_ref` がある（RULE-021）

### FND

- [ ] `found-in` 辺が存在（RULE-009/010）

### VERIFY

- [ ] `verifies` 辺が存在（RULE-013）

### NFR

- [ ] `validates` 辺（FND から）が存在（RULE-011）

---

## 5. suppress が必要なケース

| 状況 | suppress 対象 | 記述例 |
|---|---|---|
| FR に error path を作る設計意図がない | RULE-018 | `suppress: [RULE-018]  # error path なし: 外部 API は SLA 99.99% で常時稼働前提` |
| SPEC は手動確認のみ（TD 不要） | RULE-015 | `suppress: [RULE-015]  # 手動レビューのみ: TC 作成の費用対効果なし（VERIFY-xxx で代替）` |

suppress を付ける前に「本当に回避できないか」を確認する。suppress の多用は品質低下の兆候。

---

## 6. エッジ方向の注意点

```
FR  → SR     (refines)  ← FR が SR を精緻化する
SPEC → FR    (refines)  ← SPEC が FR を精緻化する
TD  → SPEC   (verifies) ← TD が SPEC を検証する
TC  → TD     (realizes) ← TC が TD を実現する
TR  → TC     (produced-by) ← TR が TC の実行から生成された

I → P (× 誤り)   正: P → I (consumes) または E → P (triggers)
PROMPT → ORC (× 誤り)   正: ORC → PROMPT (uses)
SCM → TERM (refines) (× 誤り)   正: SCM → TERM (see-also)
```
