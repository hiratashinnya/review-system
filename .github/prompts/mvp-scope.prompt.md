---
mode: 'agent'
description: 'Scope an MVP by value. List features with value/precondition/atomic-group, draw a dependency DAG, then propose build order and where to draw the MVP line. Use after features are enumerated and before development starts.'
---

# 価値ベース MVP スコープ

機能を**価値で並べ**、前提と不可分グループを明示して着手順と MVP ラインを決める。
原則：[spec-principles](../spec-principles/SKILL.md)（PR8 フル論理＋MVP印）。

## 手順
1. 機能を列挙。各々に **価値（誰に何を）・前提（先行物）・不可分グループ**（単独では価値ゼロでセット必須）を付す。
2. **依存 DAG**（前提＝矢印、前提層は点線）を描く。
3. 価値で着手順を提案（前提が重い／効果が遅延するものは後ろ）。
4. **MVP ライン**を引く。内側だけで「価値が出る」ことを確認。

## 判断基準
- 不可分グループは**丸ごと1単位**（途中までは価値ゼロ）。
- 価値未接続（その時点で出力に繋がらない）機能は MVP 外に印。
- リスクと安全機構はセット（例：自動適用と取り消しは不可分）。

## 成果物テンプレ
`ID | 機能 | 価値 | 前提 | 不可分 | 段階` の表 ＋ 依存 Mermaid ＋ 着手順 ＋ MVP ライン ＋ 後回しの根拠。
