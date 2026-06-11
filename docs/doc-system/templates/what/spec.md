---
version: "0.1.0"
---
# 機能仕様（テスタブル粒度）

> **型**: SPEC ／ **必須上流**: FR（refines ✅）
> **RULE-006 config**: TD からの `verifies` 辺が必要（カバレッジ確保）。
> **RULE-016（ERROR）**: `condition` 属性が必要（normal / boundary / failure / error）。
> 1 ノード = 1 テスト条件（1 condition）。条件をまたぐ場合は別 SPEC に分割する。
> 意図的に condition を省略・ルールを抑制するときは `suppress: [RULE-xxx]` を使い理由を inline comment に残す。

## SPEC-001: [正常系の仕様タイトル]

<details><summary>⬡ SPEC-001 · v0.1</summary>

```yaml
id: SPEC-001
type: SPEC
condition: normal     # 有効な入力・正常な状態 → 期待通りに動く
labels: []
scheduled: ""
edges:
  - to: FR-001
    ref_version: "0.1"
  # TD → SPEC-001 (verifies) は TD 側の edges に記述する（RULE-006 config の対象辺）
```
</details>

**前提条件**: [正常に動く前提・文脈]
**入力/トリガ**: [有効な入力・操作]
**期待動作**: [正常応答・状態変化]

---

## SPEC-002: [境界値の仕様タイトル]

<details><summary>⬡ SPEC-002 · v0.1</summary>

```yaml
id: SPEC-002
type: SPEC
condition: boundary   # 有効/無効の境目。pass か fail かは本文で明示
labels: []
scheduled: ""
edges:
  - to: FR-001
    ref_version: "0.1"
```
</details>

**前提条件**: [境界値が発生する文脈]
**入力/トリガ**: [上限・下限・空・最大長など境界にある値]
**期待動作**: [通過（normal 相当）か拒否（failure 相当）かを明示]

---

## SPEC-003: [不成立の仕様タイトル]

<details><summary>⬡ SPEC-003 · v0.1</summary>

```yaml
id: SPEC-003
type: SPEC
condition: failure    # 無効な入力・業務ルール違反 → 拒否応答
labels: []
scheduled: ""
edges:
  - to: FR-001
    ref_version: "0.1"
```
</details>

**前提条件**: [拒否が起きる文脈]
**入力/トリガ**: [無効な入力・違反条件]
**期待動作**: [エラーレスポンス・拒否・ロールバック等]

---

## SPEC-004: [異常系の仕様タイトル]

<details><summary>⬡ SPEC-004 · v0.1</summary>

```yaml
id: SPEC-004
type: SPEC
condition: error      # インフラ障害・タイムアウト → フェイルセーフ応答
labels: []
scheduled: ""
edges:
  - to: FR-001
    ref_version: "0.1"
```
</details>

**前提条件**: [障害・異常が発生している状態]
**入力/トリガ**: [操作または外部障害]
**期待動作**: [フェイルセーフ動作・エラーコード・ログ出力等]
