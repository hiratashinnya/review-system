---
name: doc-authoring
description: Author doc-system nodes correctly — fill meta-attributes (id/type/condition/suppress/result/log_ref), write required edges (kind/status/ref_version), and pass the relevant RULE checks. Use when creating or editing any node in docs/. Reference for per-type body structure, mandatory links, and acceptance criteria. NOT for design decisions (use align/spec-pipeline), NOT for verification sweeps (use spec-inspector).
status: active
---

# ドキュメント・オーサリング規約（doc-authoring）

> ノード作成時の標準手順。詳細な人向け解説は [07-authoring-guide.md](../../../docs/doc-system/07-authoring-guide.md)。
> スキーマ詳細 → [02-meta-schema.md](../../../docs/doc-system/02-meta-schema.md)。
> 接続要否 → [03-connection-matrix.md](../../../docs/doc-system/03-connection-matrix.md)。
> テンプレート → `docs/doc-system/templates/`。

---

## 共通手順（全ノード）

1. **テンプレを複製**：`docs/doc-system/templates/<layer>/<type>.md` からコピー。
2. **id を採番**：`PREFIX-N`（連番・永続・リネーム禁止）。既存最大番号 + 1。
3. **type を設定**：型値は §6 の表から（VAL/SR/FR/SPEC/NFR/TERM/ACTOR/I/O/P/E/ORC/DS/MOD/DM/PORT/PRS/SCM/CFG/PROMPT/TD/TC/TR/VERIFY/FND/DD/Q/PEND）。
4. **必須 edges を追加**：接続マトリクス ✅ の辺は必須（RULE-006）。`to` が存在するか確認（RULE-007）。
5. **status: pending** から始める。反映確認後に `done`。
6. **ref_version** を参照先の現在 `x.y` に合わせる。
7. **本文を書く**：前提条件・入力/トリガ・期待動作 or 該当フォーマット。
8. **RULE を通す**：下表「受け入れ条件」を満たしているか確認。

---

## 型別クイックリファレンス

### Why 層

| 型 | 必須辺 | 主な RULE |
|---|---|---|
| VAL | なし（根） | RULE-005（孤立禁止） |
| SR | → VAL (refines) | RULE-006 |

### What 層

| 型 | 必須辺 | 追加属性 | 主な RULE |
|---|---|---|---|
| FR | → SR (refines) | `suppress: [RULE-018]` 任意 | RULE-006, RULE-017（normal SPEC 必須）, RULE-018（failure/error INFO） |
| SPEC | → FR (refines) | `condition: normal\|boundary\|failure\|error` ✅ | RULE-015（TD verifies 必須）, RULE-016（condition 必須） |
| NFR | → SR (refines) | — | RULE-011（validates 辺が必要） |

> SPEC は 1 ノード = 1 condition。条件をまたぐ場合は別 SPEC に分割する。

### 分析層

| 型 | 必須辺 | 主な RULE |
|---|---|---|
| ACTOR | → SR (refines) | RULE-005 |
| I | → SPEC (refines) | RULE-005, RULE-006 |
| O | → SPEC (refines) | RULE-005, RULE-006 |
| P | → SPEC (refines) | RULE-006（I/O/E リンク必須） |
| E | → SPEC (refines) | RULE-005, RULE-006 |

> I → P は P 側が `consumes` で記述（I 側に書かない）。
> E → P は E 側が `triggers` で記述。

### 設計層

| 型 | 必須辺 |
|---|---|
| ORC | → P (refines)、→ PROMPT (uses) 任意 |
| DS | → P (refines) |
| MOD | → P (refines) |
| DM | → TERM (refines)、→ P (refines) |
| PORT | → MOD (refines) |
| PRS | → DS (refines) |
| SCM | → SPEC (refines)、→ TERM (see-also) |
| CFG | → SCM (instantiates)、→ SPEC (refines) |
| PROMPT | → SPEC (refines) |

### 検証層

| 型 | 必須辺 | 追加属性 | 主な RULE |
|---|---|---|---|
| TD | → SPEC (verifies) | `condition` ✅（SPEC の condition と一致） | RULE-012（realizes 辺は TC 側）, RULE-016, RULE-019 |
| TC | → TD (realizes) | — | RULE-012（realizes 辺が 0 本は ERROR） |
| TR | → TC (produced-by) | `result: PASS\|FAIL` ✅, `log_ref` (FAIL 時必須) | RULE-020, RULE-021 |
| VERIFY | → 対象要素 (verifies) | — | RULE-013 |
| FND | → 対象要素 (found-in) | — | RULE-009, RULE-010 |

### 横断スパイン

| 型 | 辺 | ライフサイクル |
|---|---|---|
| DD | → 影響要素 (affects) | open → decided → closed（本文に記載） |
| Q | → 影響要素 (affects) | open → deferred / decided → closed |
| PEND | → 影響要素 (affects) | deferred → open（再開）/ closed |

---

## よくある間違いと対策

| 間違い | 正しい対応 |
|---|---|
| I ノードに `kind: triggers` | triggers は E ノードのみ。I→P は P 側で `kind: consumes` |
| TC に `kind: verifies` | TC は `kind: realizes`（→ TD）。verifies は TD → SPEC |
| SPEC に condition なし | `condition: normal\|boundary\|failure\|error` を必ず付与（RULE-016） |
| TD の condition が SPEC と不一致 | verifies 先 SPEC の condition と一致させる（RULE-019） |
| TR の result がボディのみ | `result: PASS\|FAIL` を YAML メタに書く（RULE-020） |
| FAIL の TR に log_ref なし | `log_ref: <path-or-url>` を YAML メタに書く（RULE-021） |
| see-also に status: pending | see-also の status は `n/a` 固定（RULE-014） |
| 辺の to が存在しない ID | RULE-007（always_error）。必ず実在 ID を確認してから書く |

---

## suppress の書き方

```yaml
suppress: [RULE-018]   # error path なし: 外部 API は常時稼働前提（SLA 99.99%）
```

- 理由を inline comment に必ず書く。理由なき suppress は PR レビューで拒否（運用ルール）。
- `always_error`（RULE-007）は suppress 不可。
