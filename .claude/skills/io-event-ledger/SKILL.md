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
