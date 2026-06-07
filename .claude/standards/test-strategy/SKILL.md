---
name: test-strategy-standard
description: GENERIC, PROJECT-INDEPENDENT test-strategy standard (NON-ACTIVE baseline — lives under .claude/standards/, not auto-loaded). Holds the invariants and the tailoring-knob list; tailor it into .claude/skills/<name> per project.
status: standard (non-active baseline)
---

# テスト戦略（汎用標準・非活性ベースライン）

> ここは **`.claude/standards/`** 配下の**汎用標準**。auto-load されない（active 運用は skills/ のテーラリング済み版）。
> プロジェクトで使うときは **ノブを埋めて `.claude/skills/<name>/SKILL.md` へテーラリング**し、[tailoring-registry](../../tailoring-registry.md) に記録する。
> 原則：[spec-principles](../../skills/spec-principles/SKILL.md)（PR2 機構/デフォルト・PR7 失敗を握りつぶさない・PR8 消さず残す）。

## 不変条件（プロジェクトを問わず守る＝機構）

1. **unittest（関数単位を基本）**。検証可能な最小単位ごとにテストを書く。
2. **テストケースは Markdown**。1ケース＝`{ id + version + 目的 + 前提 + 手順 + 期待結果 }`。
3. **テスト成績書＝ケースをコピーして実測結果を追記**。冒頭ヘッダに
   `{ 対応ケース版 + 実装commit id + 実行日時 + 環境 }`。**ログはリンクで紐付け**。
4. **ログ＝標準出力ダンプ**。成績書からリンクして辿れる。
5. **失敗時も成績書を残す（隠蔽・上書き禁止）**。失敗成績書には **原因調査結果＋対策検討結果**を併記。
   上書きせず追記/版管理（PR8）。
6. **e2e も、エージェント等で実施可能なものは同じ3点セット**（ケース／成績書／ログ）。
7. **テスト実施前にコミット**し、成績書に**意味のある commit id** を書く。
> 3点セット（ケースMD／成績書／ログ）の**対応関係を常に保つ**。これが証跡の背骨。

## テーラリング・ノブ（プロジェクトで埋める＝デフォルト）

| ノブ | 決めること |
|---|---|
| 「1関数」の定義・網羅範囲 | 何を最小単位とし、どこまで網羅するか（全 public 関数 等） |
| 非決定の決定化シーム | 非決定要素（外部API/LLM/時刻/乱数）をどこで Fake/stub/record-replay に置換するか |
| e2e の駆動手段・対象 | 何で end-to-end を回すか（CLI/エージェント等）、どのシナリオを e2e にするか |
| ログ取得方法 | 標準出力ダンプの具体（tee・リダイレクト・キャプチャ） |
| ディレクトリ配置 | ケース／成績書／ログ／unit の置き場 |
| バージョニング | ケース版・commit id・その他版スタンプ（雛形版・設定hash 等）の紐付け方 |
| 実行コマンド/ランナー | テストの起動方法（依存方針に整合） |

## テーラリング手順（標準 → active）
1. **棚卸し**：本標準の不変条件はそのまま継承、ノブを洗い出す。
2. **置換（非活性化）**：既存の active 汎用版があれば `git mv .claude/skills/<n> .claude/standards/<n>`（消さず非活性化・PR8）。
3. **テーラリング版を author**：ノブを埋めた `SKILL.md` を `.claude/skills/<n>/` に置く（active）。
4. **registry 記録**：[tailoring-registry](../../tailoring-registry.md) に `標準源／実体パス／テーラリング内容／由来PJ` を追記。

## done（テーラリング完了の判定）
- 全ノブが埋まっている。
- 3点セット（ケースMD・成績書・ログ）のテンプレが確定している。
- 失敗時の保全フロー（隠蔽禁止・原因/対策併記）が手順化されている。
- registry に実体パスとテーラリング内容が記録済み。
</content>
