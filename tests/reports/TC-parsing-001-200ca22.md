---
id: TC-parsing-001
version: 1.0
---
# テスト成績書 — 自前フロントマター・パーサ＋lint（TC-parsing-001）

> ケース [TC-parsing-001.md](../cases/TC-parsing-001.md) のコピー＋実測。失敗時は隠さず原因/対策併記（PR8）。

## ヘッダ
| 項目 | 値 |
|---|---|
| 対応ケース版 | 1.0 |
| 実装 commit id | `200ca22` |
| prompt_template_version | — （パーサ層・LLM 不使用） |
| criteria_content_hash | — |
| 実行日時 | 2026-06-07 |
| 環境 | Python 3.11.15・標準ライブラリのみ |
| ログ | [./../logs/TC-parsing-001-200ca22.txt](../logs/TC-parsing-001-200ca22.txt) |

## 結果：**PASS**（19/19）

### パーサ（対応サブセット）
| # | 種別 | 実測 |
|---|---|---|
| P1 正常フロントマター | 正常 | PASS |
| P2 スカラ型（str/bool/null/str） | 正常 | PASS（version は文字列のまま） |
| P3 コメント無視 | 正常 | PASS |
| P4 引用内 `#` 保持 | エッジ | PASS |
| P5 タブインデント | 境界 | PASS（`MiniYamlError`） |
| P6 フロー `[a,b]` | 境界 | PASS（拒否） |
| P7 複数行 `|` | 境界 | PASS（拒否） |
| P8 アンカー `&` | 境界 | PASS（拒否） |
| P9 閉じ `---` 欠落 | 境界 | PASS（拒否） |
| P10 3スペース奇数インデント | エッジ | PASS（拒否） |

### lint（S5 検証器）
| # | 種別 | 実測 |
|---|---|---|
| L1 妥当 | 正常 | PASS（ok） |
| L2 override 不正値 | 異常 | PASS（エラー） |
| L3 severity 不正値 | 異常 | PASS |
| L4 determinism 不正値 | 異常 | PASS |
| L5 必須キー欠落 | 異常 | PASS |
| L6 id 重複 | エッジ | PASS（両 id 指摘） |
| L7 未対応 MAJOR=2 | 境界 | PASS（fail-close） |
| L8 対応 MAJOR・新 MINOR=1.9 | 境界 | PASS（ok・MINOR は情報のみ） |
| L9 extends 先なし | 異常 | PASS |

## 所見
- 「読めなかったを黙って空にしない」＝範囲外記法を**実行前に名指しで弾く**（S5）を境界群で確認。
- `version` を**整数化せず MAJOR.MINOR 文字列**で扱い、MAJOR のみで対応判定（MINOR は情報）＝[DD7](../../docs/design/decisions.md) どおり。
- FAIL なし＝原因調査/対策の記載は無し。
