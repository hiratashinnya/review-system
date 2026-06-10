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

## doc-system ノード著作（ACTOR / I / O / P / E ＋ FR / SPEC / NFR）
要件が結晶化するこの段で、**分析層**（ACTOR/I/O/P/E）と**What 層**（FR/SPEC/NFR）を著作する。共通手順・横断スパイン・RULE 全文・本文フォーマットは [07-authoring-guide.md](../../../docs/doc-system/07-authoring-guide.md)。スキーマ→[02-meta-schema.md](../../../docs/doc-system/02-meta-schema.md)、接続要否→[03-connection-matrix.md](../../../docs/doc-system/03-connection-matrix.md)。

| 型 | 必須辺 | 追加属性 | 主な RULE |
|---|---|---|---|
| ACTOR | → SR (refines) | — | RULE-005 |
| I | → SPEC (refines) | — | RULE-005/006 |
| O | → SPEC (refines) | — | RULE-005/006 |
| P | → SPEC (refines) | — | RULE-006（I/O/E リンク必須）|
| E | → SPEC (refines) | — | RULE-005/006 |
| FR | → SR (refines) | `suppress:[RULE-018]` 任意 | RULE-017（normal SPEC 必須）/018 |
| SPEC | → FR (refines) | `condition: normal\|boundary\|failure\|error` ✅ | RULE-015（TD verifies）/016 |
| NFR | → SR (refines) | — | RULE-011（FND→validates）|

> I→P は **P 側** `consumes`、E→P は **E 側** `triggers`（I/E 側に書かない）。SPEC は **1 ノード=1 condition**（条件をまたぐなら別 SPEC へ分割）。
