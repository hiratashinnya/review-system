---
id: TC-domain-001
version: 1.0
---
# テスト成績書 — ドメイン基盤（TC-domain-001）

> ケース仕様 [TC-domain-001.md](../cases/TC-domain-001.md) のコピー＋実測。失敗時は隠さず原因/対策を併記（PR8）。

## ヘッダ（版スタンプ・S6 と同語彙）
| 項目 | 値 |
|---|---|
| 対応ケース版 | 1.0 |
| 実装 commit id | `b5fa2cd` |
| prompt_template_version | — （ドメイン層・LLM 不使用） |
| criteria_content_hash | — （同上） |
| 実行日時 | 2026-06-07 |
| 環境 | Python 3.11.15・標準ライブラリのみ |
| ログ | [./../logs/TC-domain-001-b5fa2cd.txt](../logs/TC-domain-001-b5fa2cd.txt) |

## 結果：**PASS**（22/22）

| # | 対象 | 種別 | 実測 |
|---|---|---|---|
| 1 | `RuleId` 値等価・hashable | 正常 | PASS |
| 2 | `RuleId` 空 | 境界 | PASS（`ValueError`） |
| 3 | `LineRange` start=end=1 | 境界（下限） | PASS |
| 4 | `LineRange` start=0 | 境界 | PASS（`ValueError`） |
| 5 | `LineRange` end<start | エッジ | PASS（`ValueError`） |
| 6 | `LineRange` 1..100 | 正常 | PASS |
| 7 | `Location` line 任意 | 正常 | PASS |
| 8 | `Location` hashable・set 縮退 | 正常 | PASS |
| 9 | `Scope` ORG/name=None | エッジ | PASS |
| 10 | `Scope` ORG＋name | 矛盾 | PASS（`ValueError`） |
| 11 | `Scope` TEAM/name=None | 矛盾 | PASS（`ValueError`） |
| 12 | `Scope` TEAM/空名 | エッジ | PASS（`ValueError`） |
| 13 | `Scope.org()` | 正常 | PASS |
| 14 | `Severity` 順序 | 正常 | PASS（IntEnum 比較） |
| 15 | `ExecutionId.of` hash12 | 正常 | PASS |
| 16 | `ExecutionId.of` hash<12 | エッジ | PASS（切れない） |
| 17 | `FindingId.of` 導出・安定 | 正常 | PASS |
| 18 | `resolve_document_type` 手動優先 | 正常 | PASS |
| 19 | 推定フォールバック | 正常 | PASS |
| 20 | 両欠→None | 境界 | PASS（fail-close 用） |
| 21 | `ok(42)` | 正常 | PASS |
| 22 | `fail(...)`・match 分岐 | 正常 | PASS |

## 所見
- 値オブジェクトが**壊れた値を生成時に弾く**（S1/S5 の土台）ことを境界で確認。
- `Location`/`RuleId` が hashable＝dict キー/set で使える（[01 §10](../../docs/design/01-class-design.md) の自動 `__eq__`/`__hash__`）。
- FAIL なし＝原因調査/対策の記載は無し。
