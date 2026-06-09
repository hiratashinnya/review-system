---
version: "0.1.0"
---
# 機能仕様（テスタブル粒度）

> **型**: SPEC ／ **必須上流**: FR（refines ✅）
> **RULE-015**: TD からの `verifies` 辺が必要（カバレッジ確保）。
> 1 ノード = テスト可能な1条件（入力・前提・期待動作が特定できる粒度）。

## SPEC-001: [仕様タイトル]

<details><summary>⬡ SPEC-001 · v0.1</summary>

```yaml
id: SPEC-001
type: SPEC
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

## SPEC-002: [仕様タイトル]

<!-- 同一 FR に複数の SPEC を持てる（境界値・正常系・異常系 等） -->
