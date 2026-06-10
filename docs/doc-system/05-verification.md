---
version: "0.1.0"
---
# 検証戦略

> ドキュメントグラフの健全性を機械＋人の組み合わせで継続検証する戦略。
> RULE の完全定義は [02 §9](02-meta-schema.md)、トレース対象集合は [06](06-trace-scope.md)。

---

## 1. 検証の目的と全体像

**腐敗源**：「実装が変わったのに設計書に反映し忘れる」ドリフト。  
**対策**：辺に `ref_version` と `status` を持たせ、グラフ走査で不整合を機械検出する。

```
ドキュメント変更
    ↓
① 辺のドリフト検出（ref_version 不一致・pending 残存）
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

**目的**：辺の `ref_version` と参照先ファイルの現在バージョンが食い違う「ドリフト」を検出する。

| RULE | 対象 | 深刻度 |
|---|---|---|
| RULE-001 | DD の affects 辺に pending 残存 | ERROR |
| RULE-002 | Q の affects 辺に pending 残存 | WARNING |
| RULE-003 | 辺の ref_version と参照先 x.y の不一致 | WARNING |
| RULE-004 | 主要辺（refines/realizes/verifies）の ref_version 不一致 | ERROR |

**トリガ**：ファイルの `version` を上げたとき（x または y の上昇）。  
**運用**：PR 差分で `version` 変更を含むコミットの後、走査を実行する。

---

### 段階 ②：構造的完結性チェック

**目的**：孤立ノード・存在しない ID への参照・必須辺の欠如を検出する。

| RULE | 対象 | 深刻度 |
|---|---|---|
| RULE-005 | VAL/ACTOR/I/O/E の孤立（辺 0 本） | ERROR |
| RULE-006 | 接続マトリクス ✅ の辺が欠如 | ERROR |
| RULE-007 | 辺の to が存在しない ID を参照 | ERROR（always_error） |
| RULE-008 | 階層 ID の親に decomposes 辺なし | WARNING |
| RULE-009 | FND に found-in/validates 辺が 0 本 | ERROR |
| RULE-010 | FND に found-in 辺なし | WARNING |
| RULE-011 | NFR に validates 辺なし | WARNING |
| RULE-012 | TC に realizes 辺なし | ERROR |
| RULE-013 | VERIFY に verifies 辺なし | ERROR |
| RULE-014 | see-also 辺に pending/done ステータス | WARNING |

**トリガ**：ノードの追加・辺の追加/削除後。  
**運用**：CI で常時実行する（ERROR があればマージブロック推奨）。

---

### 段階 ③：仕様カバレッジ検証

**目的**：SPEC に対するテスト設計（TD）の紐づき漏れと、condition 軸のカバレッジ穴を検出する。

| RULE | 対象 | 深刻度 |
|---|---|---|
| RULE-015 | SPEC に TD からの verifies 辺なし | WARNING |
| RULE-016 | SPEC/TD に condition 属性なし | WARNING |
| RULE-017 | FR に condition: normal の SPEC なし | WARNING |
| RULE-018 | FR に condition: failure/error の SPEC なし | INFO |
| RULE-019 | TD の condition が verifies 先 SPEC の condition と不一致 | WARNING |
| RULE-020 | TR に result 属性なし | WARNING |
| RULE-021 | TR が FAIL かつ log_ref なし | WARNING |

**出力イメージ**：

```
カバレッジレポート
FR-001:
  ✅ normal   — SPEC-001 ← TD-001
  ✅ boundary — SPEC-002 ← TD-002
  ⚠️ failure  — SPEC-003 ← (TD なし) [RULE-015]
  — error    — (SPEC なし) [RULE-018 INFO]

TR 完結性:
  ✅ TR-001 result: PASS  log_ref: ci/logs/run-1.txt
  ⚠️ TR-002 result: FAIL  log_ref: (なし) [RULE-021]
```

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
  - to: [FR-001, SPEC-001, SPEC-002]
    kind: verifies
    status: done
    ref_version: "1.0"
```

**本文**：検証範囲・手法・実施日・結果を記載。指摘があれば FND を起票して参照する。

### FND（指摘）

VERIFY または TC/TR の実行中に発見した指摘を記録する。

```yaml
id: FND-001
type: FND
edges:
  - to: SPEC-003
    kind: found-in
    status: pending
    ref_version: "1.0"
  - to: NFR-002        # 任意: この NFR が満たされていない証拠
    kind: validates
    status: done
    ref_version: "1.0"
```

**本文**：内容・深刻度（critical/major/minor/info）・状態（open/resolved/wontfix）・対処を記載。

---

## 5. NFR 検証フロー（§11）

すべての NFR に少なくとも1本の `validates` 辺が必要（RULE-011）。

```
NFR-001（性能制約）
  ← FND-001 (validates) — 性能テストで確認した指摘
  ← TR-012 (validates)  — ベンチマーク実行結果

NFR-002（セキュリティ制約）
  ← VERIFY-003 (validates) — セキュリティレビュー実施記録
```

> `validates` 辺は **FND・TR・VERIFY のいずれ**から来ても良い。  
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
| `stage_scope` | 現フェーズで対象外の型は WARNING 降格 | ERROR → WARNING |
| `suppress` | ノード単位で特定ルールを抑制 | 完全サイレント（理由 comment 必須） |

> 抑制数が増えすぎると品質低下の兆候。月次で抑制ノードを棚卸しする（運用ルール）。
