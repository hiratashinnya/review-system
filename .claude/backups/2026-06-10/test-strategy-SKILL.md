---
name: test-strategy
description: Test strategy for THIS project (review-system) — unittest per public function, Markdown test cases, a test report = case copy + result with commit-id/case-version, stdout log link, keep failures with root-cause + countermeasure, commit-before-test, same 3-set for Claude Code e2e. Use when planning HOW to test the implementation. NOT spec/design (see domain-model/schema-design), NOT asset auditing (see asset-auditor).
status: tailored (active) — derived from .claude/standards/test-strategy
---

# テスト戦略（review-system テーラリング済・active）

> 汎用標準 [`.claude/standards/test-strategy`](../../standards/test-strategy/SKILL.md) の**不変条件を継承**し、本PJのノブを埋めた版。
> 由来・差分は [tailoring-registry](../../tailoring-registry.md)。実装の足場は [design/02 モジュール構成](../../../docs/design/02-module-architecture.md)。

## 継承する不変条件（標準のまま）
unittest 基本／ケース＝Markdown／成績書＝ケースコピー＋実測＋commit id／ログ＝標準出力ダンプをリンク／
失敗も残す（隠蔽・上書き禁止＋原因/対策）／e2e も同じ3点セット／**テスト前にコミット**。3点セットの対応を保つ。

## 本PJのノブ（埋めた値）

| ノブ | 本PJの決定 |
|---|---|
| 「1関数」の定義・網羅 | `domain` / `core` / `parsing` / `prompts` の**全 public 関数**を unittest（[02](../../../docs/design/02-module-architecture.md) の内向き依存で純粋なので関数単位で回せる） |
| 非決定の決定化シーム | **`adapters/fake.py` の `FakePlatformAdapter`（record/replay フィクスチャ）**。非決定は LLM のみ＝`PlatformPort` の裏。**アダプタ境界＝テスト境界**にして core を決定化（[10 境界](../../../docs/requirements/10-llm-system-boundary.md)・E） |
| e2e の駆動・対象 | **Claude Code エージェントが `io/cli` を stdout 駆動で実行**。対象＝代表レビューシナリオ（合成→評価→仕分け→適用→レポート）。3点セットを残す |
| ログ取得 | **標準出力ダンプ**。`python -m unittest -v` 出力＋アプリ stdout を `tee` で `tests/logs/<case>-<commit>.txt` に保存 |
| ディレクトリ配置 | `tests/unit/`（関数）・`tests/cases/*.md`（ケース）・`tests/reports/*.md`（成績書）・`tests/logs/*.txt`（ログ） |
| バージョニング | ケースMD frontmatter に `version`。成績書ヘッダに **`{ ケース版 + 実装commit id + プロンプト雛形版 + 基準content_hash(S6) + 実行日時 }`**（[S6 版スタンプ](../../../docs/requirements/13-stabilization.md) と一致） |
| 実行ランナー | **`python -m unittest`**（標準ライブラリのみ・[Q5](../../../docs/dashboard.md)） |

## 3点セットのテンプレ（本PJ）

**ケース** `tests/cases/<id>.md`
```
---
id: TC-<area>-<nnn>
version: 1
---
# 目的 / 前提 / 手順 / 期待結果
```
**成績書** `tests/reports/<id>-<commit>.md` … ケースを丸ごとコピーし末尾に
```
## 実測
- ヘッダ: { ケース版 / 実装commit id / プロンプト雛形版 / 基準content_hash / 実行日時 / 環境 }
- 結果: PASS|FAIL
- ログ: ./../logs/<id>-<commit>.txt
- （FAIL時）原因調査 / 対策検討   ← 隠蔽・上書き禁止（PR8）
```
**ログ** `tests/logs/<id>-<commit>.txt` … stdout ダンプ。

## 手順（1サイクル）
1. 実装を**コミット**（commit id を確定）。
2. `python -m unittest -v 2>&1 | tee tests/logs/<id>-<commit>.txt`。
3. ケースをコピーして成績書を作成、ヘッダ＋結果＋ログリンクを記入。
4. FAIL は成績書を残し、原因調査・対策検討を併記（消さない・上書きしない）。
5. e2e は Claude Code エージェントで `io/cli` を回し、同じ3点セットを残す。
</content>
