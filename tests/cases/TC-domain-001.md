---
id: TC-domain-001
version: 1.0
---
# ドメイン基盤（値オブジェクト・Enum・Result・調停）

> 対象：`review_system.domain`（[design/01](../../docs/design/01-class-design.md)）。境界値・エッジケースを含む。

## 目的
型で不変条件を守る基盤（値オブジェクトの検証・Enum の順序・Result の fail-close・型調停）が、**壊れた値を作らせず**、境界条件で正しく振る舞うことを確認する。

## 前提
- Python 3.11・標準ライブラリのみ（[Q5](../../docs/dashboard.md)）。
- パスは `pathlib.Path`（[DD13](../../docs/design/decisions.md)）。

## 手順
`python -m unittest -v tests.unit.test_domain`

## 期待結果（ケース一覧・境界/エッジ明示）

| # | 対象 | 入力 | 期待 |
|---|---|---|---|
| 1 | `RuleId` | `"naming"` | 生成成功・値等価（`RuleId("naming")==RuleId("naming")`） |
| 2 | `RuleId` 境界 | `""`（空） | `ValueError`（空は不可） |
| 3 | `LineRange` 境界 | `start=1,end=1` | 成功（単一行・下限） |
| 4 | `LineRange` 境界 | `start=0` | `ValueError`（行は1始まり） |
| 5 | `LineRange` エッジ | `start=5,end=4`（end<start） | `ValueError` |
| 6 | `LineRange` | `start=1,end=100` | 成功 |
| 7 | `Location` | `file=Path("a.py")`, line_range=None | 成功（line 任意） |
| 8 | `Location` ハッシュ | 同値2個 | `==` True かつ set で1個に縮退（hashable） |
| 9 | `Scope` エッジ | `ORG`＋name=None | 成功 |
| 10 | `Scope` 矛盾 | `ORG`＋name="x" | `ValueError`（org は名前を持たない） |
| 11 | `Scope` 矛盾 | `TEAM`＋name=None | `ValueError`（team は名前必須） |
| 12 | `Scope` エッジ | `TEAM`＋name=""（空） | `ValueError`（空名は不可） |
| 13 | `Scope.org()` | — | `layer==ORG, name is None` |
| 14 | `Severity` 順序 | `ERROR,WARNING,INFO` | `ERROR>WARNING>INFO`（IntEnum 比較） |
| 15 | `ExecutionId.of` | `("2026-06-07T00:00:00Z", hash="abcdef0123456789")` | `"…-abcdef012345"`（hash 先頭12） |
| 16 | `ExecutionId.of` エッジ | hash="abc"（12未満） | hash 全体を採用（切れない） |
| 17 | `FindingId.of` | finding(rule_id, location) | `rule_id+location` から導出・同 finding は同 id |
| 18 | `resolve_document_type` | manual=SPEC, est=CODE | **SPEC**（手動上書き優先） |
| 19 | `resolve_document_type` | manual=None, est=CODE(0.9) | **CODE**（推定フォールバック） |
| 20 | `resolve_document_type` 境界 | manual=None, est=None | **None**（呼出側で fail-close） |
| 21 | `Result` | `ok(42)` | `Success(value=42)` |
| 22 | `Result` | `fail(...)` | `Failure(notice=...)`・`match` で分岐可 |
</content>
