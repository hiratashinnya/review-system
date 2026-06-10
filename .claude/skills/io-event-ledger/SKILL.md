---
name: io-event-ledger
description: Build an I/O ledger (classify inputs, attach originating source) and an event-response list (trigger→reaction→output→value), then run a coverage cross-check. Use early when requirements start to settle.
---

# I/O 台帳 ＋ イベントリスト

入出力を1か所に集約し、外部イベントとの対応で抜けを炙り出す。
原則：[spec-principles](../spec-principles/SKILL.md)（PR1 もので分ける・PR3 系外・PR4 観測不能）。

## 手順
1. **I/O 台帳**：入力を分類（評価対象／中身の定義／コンフィグ／人間FB 等）。各入力に**発生源（外部アクター）**を付す。出力を列挙。状態と関連論点を付す。
2. **イベントリスト**：外部トリガごとに `# | トリガ | アクター | 種別(実/時/例外) | 反応 | 出力 | 生む価値`。
3. **カバレッジ点検**：(a) 各出力が何かのイベントから駆動されるか (b) 各入力が使われるか (c) 反応未定義のイベント＝穴 → 論点化。

## 判断基準（PR1）
- もの＋発生源で分ける。**使い道・内部プロセスで分けない**。発生源が外部システム/LLM なら入力。
- 系外の変更はイベントにしない（PR3）。観測不能な事象はイベントにしない（PR4）。
- 設定ファイルのフロントマター項目は親ファイルの中身＝別入力にしない。

## 成果物
入力表（発生源列つき）／出力表／イベント表／カバレッジ表＋穴の一覧。
点検は **spec-inspector** サブエージェントに回せる。

## ノード著作（ACTOR / I / O / P / E ＋ FR / SPEC / NFR）

**共通手順**
1. テンプレ複製：`docs/doc-system/templates/<layer>/<type>.md`
2. id 採番：`PREFIX-N`（連番・永続・変更禁止）、既存最大 +1
3. 必須 edges を追加（下表）。`to` が実在する id か確認（RULE-007: always_error）
4. SPEC・TD は `condition` 属性必須（RULE-016）
5. status: pending から始め、反映確認後に done
6. ref_version を参照先の現在 `x.y` に合わせる
7. 受け入れ条件を確認（下表）

| 型 | 必須辺 | 追加属性 | 主な RULE |
|---|---|---|---|
| ACTOR | → SR (refines) | — | RULE-005（孤立禁止）|
| I | → SPEC (refines) | — | RULE-005/006 |
| O | → SPEC (refines) | — | RULE-005/006 |
| P | → SPEC (refines) | — | RULE-006（I/O/E リンク必須）|
| E | → SPEC (refines) | — | RULE-005/006 |
| FR | → SR (refines) | `suppress:[RULE-018]` 任意 | RULE-017（normal SPEC 必須）/018 |
| SPEC | → FR (refines) | `condition: normal\|boundary\|failure\|error` ✅ | RULE-015（TD verifies 必須）/016 |
| NFR | → SR (refines) | — | RULE-011（FND→validates 辺必要）|

**本文フォーマット**

```
# ACTOR
[外部エンティティの役割・範囲]

# I
**もの**: [入力の実体]
**発生源**: [どのアクタから]
**形式**: [型・フォーマット]
**タイミング**: [いつ・どのトリガで]

# O
**もの**: [出力の実体]
**受け手**: [どのアクタが受け取るか]
**形式**: [型・フォーマット]

# P
[単一責務を1文（〜を〜する）]
**入力**: I-xxx を消費（consumes）
**出力**: O-xxx を生成（produces）
**トリガ**: E-xxx から起動（triggers）

# E
**トリガ**: [外部トリガの内容]
**反応**: [システムの反応]

# FR
[システムが持つべき機能・ユーザー価値を1文]
（FR は「なぜこの機能が必要か」粒度。テスタブル条件は SPEC へ分割する）

# SPEC
**前提条件**: [正常に動く前提・文脈]
**入力/トリガ**: [有効な入力・操作]
**期待動作**: [正常応答・状態変化]
（1 ノード = 1 condition。条件をまたぐなら別 SPEC へ分割）

# NFR
[制約の内容：性能・技術選択・安全デフォルト等]
```

**辺方向の注意**
- I → P は**誤り**。正：P 側が `kind: consumes`（I → P と書かない）
- E → P は**誤り**。正：E 側が `kind: triggers`
- suppress を使う場合は inline comment に理由必須。RULE-007 は suppress 不可（always_error）

**受け入れ条件**
- [ ] id 一意、type 一致、edges の to がすべて実在（RULE-007）
- [ ] 接続マトリクス ✅ の辺がすべて存在（RULE-006）
- [ ] SPEC に `condition` 属性あり（RULE-016）
- [ ] SPEC に TD からの `verifies` 辺が存在（RULE-015）
- [ ] FR に `condition: normal` の SPEC が少なくとも1本（RULE-017）
- [ ] see-also 辺の status が `n/a`（RULE-014）
- [ ] ref_version が参照先の現在バージョンと一致（RULE-003/004）
