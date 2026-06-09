---
version: "0.1.0"
---
# 機能仕様（テスタブル粒度）

> **型**: SPEC ／ **必須上流**: FR（refines ✅）
> **RULE-015**: TD からの `verifies` 辺が必要（カバレッジ確保）。
> **RULE-016**: `scenario` 属性が必要（normal / failure / error）。
> 1 ノード = テスト可能な1条件（1シナリオ）。シナリオをまたぐ場合は別 SPEC に分割する。

## SPEC-001: [仕様タイトル]

<details><summary>⬡ SPEC-001 · v0.1</summary>

```yaml
id: SPEC-001
type: SPEC
scenario: normal      # 必須推奨: normal | failure | error（RULE-016）
labels: []
scheduled: ""
edges:
  - to: FR-001          # 必須: この仕様が詳細化する機能要求
    kind: refines
    status: pending
    ref_version: "0.1"
  # TD → SPEC-001 (verifies) は TD 側の edges に記述する（RULE-015 の対象辺）
```
</details>

**前提条件**: [テスト実行前に満たすべき状態・文脈]
**入力/トリガ**: [何を与えるか・何が起きるか]
**期待動作**: [システムが示すべき振る舞い・出力・状態変化]

---

## SPEC-002: [失敗系の仕様タイトル]

<details><summary>⬡ SPEC-002 · v0.1</summary>

```yaml
id: SPEC-002
type: SPEC
scenario: failure     # バリデーション失敗・業務ルール違反
labels: []
scheduled: ""
edges:
  - to: FR-001
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: [失敗を引き起こす前提]
**入力/トリガ**: [不正な入力や違反条件]
**期待動作**: [エラーレスポンス・拒否・ロールバック等]

---

## SPEC-003: [異常系の仕様タイトル]

<details><summary>⬡ SPEC-003 · v0.1</summary>

```yaml
id: SPEC-003
type: SPEC
scenario: error       # インフラ障害・タイムアウト・予期しない例外
labels: []
scheduled: ""
edges:
  - to: FR-001
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: [障害・異常が発生している状態]
**入力/トリガ**: [操作または外部障害]
**期待動作**: [フェイルセーフ動作・エラーコード・ログ出力等]
