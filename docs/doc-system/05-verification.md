# 検証戦略

> ドキュメントグラフの健全性を機械＋人の組み合わせで継続検証する戦略。
> RULE の完全定義は [02 §9](02-meta-schema.md)、トレース対象集合は [06](06-trace-scope.md)。

---

## 1. 検証の目的と全体像

**腐敗源**：「実装が変わったのに設計書に反映し忘れる」ドリフト。  
**対策**：辺に `ref_version` を持たせ、グラフ走査で不整合を機械検出する（status は廃止・ref_version が真実源）。

```
ドキュメント変更
    ↓
① 辺のドリフト検出（ref_version 不一致・DD/Q/PEND 義務辺の残存）
    ↓
② 構造的完結性チェック（孤立ノード・必須辺の欠如）
    ↓
③ 仕様カバレッジ検証（SPEC×condition に TD が紐づくか）
    ↓
④ コード⇔設計の構造比較（実装着手後 — sub-issue）
```

---

## 2. 段階別検証（①②③ 先行・④ は sub-issue）

### 段階 ①：ドリフト検出

**目的**：辺の `ref_version` と参照先**ノードの現在バージョン（summary バッジ x.y）**が食い違う「ドリフト」を検出する（DD-8：ファイル version は廃止・ノード単位の版が基準）。

| RULE | 対象 | 深刻度 |
|---|---|---|
| RULE-001 | DD の義務辺（`DD→X`）が存在（未反映） | ERROR |
| RULE-002 | Q の義務辺（`Q→X`）が存在 | WARNING |
| RULE-022 | PEND の義務辺（`PEND→X`）が存在 | WARNING |
| RULE-004 | 辺の ref_version と参照先**ノード**の x.y（バッジ）の不一致（全依存辺・義務辺含む・DD-8） | ERROR |

> RULE-003 廃止（→ RULE-004）。see-also 廃止で辺は全て依存辺＝ドリフトは一律 ERROR。

**トリガ**：ノードのバッジ `vX.Y.Z` を上げたとき（x・y・z の上昇・DD-8）。  
**運用**：PR 差分でノードバッジ変更を含むコミットの後、走査を実行する。

---

### 段階 0：パース検証

**目的**：グラフ構築前に、ファイルおよびノード YAML の構造的異常を検出する。段階①②③より先に実行し、異常があれば fail-close（処理中断）する。

| RULE | 対象 | 深刻度 |
|---|---|---|
| RULE-023 | ノード YAML が PyYAML safe_load でパース不能（構文エラー） | ERROR（fail-close） |
| RULE-024 | `⬡` マーカーが存在するが直後に ``` yaml ``` ブロックが存在しない | ERROR（fail-close） |
| RULE-025 | ノード YAML に `id` フィールドが存在しない（または空文字） | ERROR |
| RULE-026 | ノード YAML に `type` フィールドが存在しない（または空文字） | ERROR |
| RULE-027 | 辺エントリに `ref_version` フィールドが存在しない | ERROR |
| RULE-028 | ノード YAML の共通必須フィールド（`labels` / `scheduled` / `edges`）が欠如、または型不正（`labels` が非リスト・`scheduled` が非文字列・`edges` が非リスト） | ERROR |
| RULE-029 | ノード YAML の `scheduled` が非空文字列かつ `config.yaml` の `phases` リストに定義されていない値（例: phases から除去された `"post-mvp"`・誤記等） | ERROR |

> RULE-023/024 は fail-close（当該ファイルのパースを中断し、後続 RULE を発火させない）。
> RULE-025/026/027/028 は後続 RULE を発火させないが他ファイルの処理は継続する（ファイル単位の fail-close）。
> RULE-023/024 は `always_error` 相当（suppress/scheduled/activate_stage 不可）。
> RULE-025/026/027 は `id`/`type`/`ref_version` の存在を、RULE-028 は残りの共通必須フィールド（`labels`/`scheduled`/`edges`）の存在と型を検証する（フィールドスキーマの完全定義を in-graph 化）。
> RULE-029 は `scheduled` の値ドメイン検証（RULE-028 の型検査の後続・FND-78/DD-9）。空文字列（`""`）は「現スプリント実施・繰り越しなし」を意味し合法。非空で phases 外＝違反。

**トリガ**：ファイルの読み込み時（段階①の前）。

---

### 段階 ②：構造的完結性チェック

**目的**：孤立ノード・存在しない ID への参照・必須辺の欠如を検出する。

| RULE | 対象 | 深刻度 |
|---|---|---|
| RULE-005 | 完全孤立（in/out 辺 0 本） | ERROR（always_error） |
| RULE-006 | config `must_link_to`/`must_be_linked_from` の必須接続欠如 | 行ごと（error/warning） |
| RULE-007 | 辺の to が存在しない ID を参照 | ERROR（always_error） |
| RULE-008 | 階層 ID `X-N` の親ノードが存在しない | ERROR |

> 旧 RULE-009/010/011/012/013/015 は RULE-006（config 駆動）に吸収。RULE-014 は see-also 廃止で消滅。

**トリガ**：ノードの追加・辺の追加/削除後。  
**運用**：CI で常時実行する（ERROR があればマージブロック推奨）。

---

### 段階 ③：仕様カバレッジ検証

**目的**：SPEC に対するテスト設計（TD）の紐づき漏れと、condition 軸のカバレッジ穴を検出する。

| RULE | 対象 | 深刻度 |
|---|---|---|
| （SPEC←TD カバレッジ） | `must_be_linked_from: SPEC ← [TD]`（旧 RULE-015） | WARNING（config 行） |
| RULE-016 | SPEC/TD に condition 属性なし | ERROR |
| RULE-017 | FR に condition: normal の SPEC なし | WARNING |
| RULE-018 | FR に condition: failure/error の SPEC なし | WARNING |
| RULE-019 | TD の condition が verifies 先 SPEC の condition と不一致 | WARNING |
| RULE-020 | TR に result 属性なし | ERROR |
| RULE-021 | TR に log_ref なし（result 問わず） | ERROR |

**出力イメージ**：

```
カバレッジレポート
FR-001:
  ✅ normal   — SPEC-001 ← TD-001
  ✅ boundary — SPEC-002 ← TD-002
  ⚠️ failure  — SPEC-003 ← (TD なし) [must_be_linked_from]
  ⚠️ error    — (SPEC なし) [RULE-018]

TR 完結性:
  ✅ TR-001 result: PASS  log_ref: ci/logs/run-1.txt
  ❌ TR-002 result: FAIL  log_ref: (なし) [RULE-021 ERROR]
```

---

### 段階 ③′：NFR 由来本文検査（`{NFR-id}-check`）

**目的**：NFR-1〜6 を機械検証可能な制約に落とした本文検査（DD-5 で NFR→SPEC 導出を制度化）。これらは構造ルール（RULE-NNN）とは別系統で、出力行3列目の rule-id に **`{NFR-id}-check`** 体系を用いる（DD-11・FND-86：番号付き RULE を新設せず NFR へ直接トレース可能な命名を採用）。検証アサーションは SPEC-44〜49（各 NFR 1件・傘＋子）。

| rule-id | 対象（NFR） | 検証 SPEC | 深刻度 |
|---|---|---|---|
| `NFR-1-check` | ノードファイルは UTF-8 プレーンテキスト .md（BOM=WARNING／デコードエラー=ERROR） | SPEC-44 | ERROR / WARNING |
| `NFR-2-check` | spec-inspector は Python 標準ライブラリのみ（外部 import 検出） | SPEC-45 | ERROR |
| `NFR-3-check` | スキルファイルは外部参照なしに自己完結（外部参照パターン検出） | SPEC-46 | WARNING |
| `NFR-4-check` | 全ノードの summary バッジに version（x.y.z）が存在・形式適合 | SPEC-47 | ERROR |
| `NFR-5-check` | 各ノードは直接の親のみへ辺を張る（USDM 1段制約） | SPEC-48 | ERROR |
| `NFR-6-check` | DD/Q/PEND のノード YAML（メタ属性）に status 系キーが存在しない | SPEC-49 | WARNING |

> rule-id は `{NFR-id}-check`（例 `NFR-1-check`）。構造ルール（RULE-NNN）とは名前空間が異なり、対応 NFR へ一意にトレースできる（DD-11）。将来 RULE-NNN 採番へ切替える場合は SPEC-44〜49 の出力例6件・本表・関連 TC を一括改修する（DD-11 影響範囲）。

**トリガ**：NFR 対象成果物（in-graph ノード／spec-inspector 実装ソース／スキルファイル）の変更後。

---

### 段階 ④：コード⇔設計の構造比較（sub-issue）

**目的**：SRC（docstring の `@id`）が DM/PORT/ORC を正しく参照しているか確認する。

- ソースの `@id` アノテーション → DM/PORT/ORC への `realizes` 辺を検証
- 実装されているが設計ノードがない SRC = 設計漏れ検出
- 設計ノードがあるが `realizes` 辺がない = 未実装または紐づけ漏れ

> 実装着手前は対象なし。実装フェーズで別 issue として計画する。

---

## 3. 機械検証の範囲と限界

### 機械が検証できるもの

| 種別 | 内容 |
|---|---|
| グラフ構造 | 孤立ノード・必須辺の欠如・存在しない ID 参照 |
| バージョンドリフト | ref_version と参照先バージョンの不一致 |
| カバレッジ | SPEC に condition:normal の TD があるか |
| TR 完結性 | result/log_ref の有無 |

### 機械が検証できないもの（人が確認）

| 種別 | 内容 | 手段 |
|---|---|---|
| 意味的正確性 | 本文の内容が正しいか・矛盾していないか | VERIFY ノード（レビュー） |
| NFR の充足 | 制約が実際に満たされているか | FND ノード（テスト結果・調査） |
| ログ内容 | TR の log_ref が指すログの中身 | CI ツール側の責務（doc-system スコープ外） |
| 設計選択の妥当性 | FR/SPEC の粒度・分割が適切か | DD/Q を用いたレビュー |

---

## 4. VERIFY・FND ノードの使い方

### VERIFY（ドキュメント検証実施）

ドキュメントを人手でレビューしたとき、または spec-inspector の走査を実施したときに記録する。

```yaml
id: VERIFY-001
type: VERIFY
edges:
  - to: FR-001
    ref_version: "1.0"
  - to: SPEC-001
    ref_version: "1.0"
  - to: SPEC-002
    ref_version: "1.0"
```

**本文**：検証範囲・手法・実施日・結果を記載。指摘があれば FND を起票して参照する。

### FND（指摘）

VERIFY または TC/TR の実行中に発見した指摘を記録する。矛盾は FND の複数辺で表す（旧 contradicts 廃止）。

```yaml
id: FND-001
type: FND
edges:
  - to: SPEC-003       # 指摘が見つかった要素
    ref_version: "1.0"
  - to: NFR-002        # この NFR が満たされていない証拠
    ref_version: "1.0"
```

**本文**：内容・深刻度（critical/major/minor/info）・状態（open/resolved/wontfix）・対処を記載。

---

## 5. NFR 検証フロー（§11）

すべての NFR は FND/TC/VERIFY のいずれかから辺を受ける必要がある
（config `must_be_linked_from: NFR ← [FND, TC, VERIFY]`・旧 RULE-011）。

```
NFR-001（性能制約）
  ← FND-001 — 性能テストで確認した指摘
  ← TR-012  — ベンチマーク実行結果

NFR-002（セキュリティ制約）
  ← VERIFY-003 — セキュリティレビュー実施記録
```

> 辺は **FND・TC・VERIFY のいずれ**から来ても良い（OR）。  
> 検証方法（テスト/レビュー/監査）をフローで制限しない。

---

## 6. 検証ツール実装計画

```
段階 ① + ②：まず実装（ドリフト検出 + 構造チェック）
  → Python CLI（標準ライブラリのみ）
  → 出力: ERROR/WARNING/INFO の一覧、終了コード 1 (ERROR あり) / 0 (なし)

段階 ③：次に追加（カバレッジレポート）
  → 段階 ①② と同一 CLI の --coverage オプション

段階 ④：実装フェーズで別途（sub-issue）
  → ソース @id アノテーションのパーサが必要
```

**入力**：`docs/` 配下の `.md` ファイル（トレース対象集合 → [06](06-trace-scope.md)）  
**出力**：deep-severity 順（ERROR → WARNING → INFO）にソートした一覧

---

## 7. 抑制の運用

ルールが誤検出になるケースは suppression で対応する（[02 §8](02-meta-schema.md) 参照）。

| 抑制軸 | 使い方 | 効果 |
|---|---|---|
| `scheduled` | 将来フェーズのノードは現在は検証対象外 | 完全サイレント |
| ステージ発火 | config の `activate_stage`/`rule_activation` が current_stage 未達 | 未到達ルールは沈黙（旧 stage_scope.disable を代替） |
| `suppress` | ノード単位で特定ルールを抑制 | 完全サイレント（理由 comment 必須・always_error 不可） |

> 抑制数が増えすぎると品質低下の兆候。月次で抑制ノードを棚卸しする（運用ルール）。
