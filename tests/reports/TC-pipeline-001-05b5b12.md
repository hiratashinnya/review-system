---
id: TC-pipeline-001
version: 1.0
---
# テスト成績書 — P1 通し（TC-pipeline-001）

ケース [TC-pipeline-001.md](../cases/TC-pipeline-001.md) のコピー＋実測。非決定は FakePlatformAdapter で決定化（E）。

## ヘッダ
| 項目 | 値 |
|---|---|
| 対応ケース版 | 1.0 |
| 実装 commit id | `05b5b12` |
| prompt_template_version | review:3.1（スタンプに記録） |
| 実行日時 | 2026-06-07 |
| 環境 | Python 3.11.15・標準ライブラリのみ |
| ログ | [./../logs/TC-pipeline-001-05b5b12.txt](../logs/TC-pipeline-001-05b5b12.txt) |

## 結果：PASS（6/6）
| # | シナリオ | 実測 |
|---|---|---|
| 1 | happy（auto/judge/ghost） | PASS（auto1・judge1・unclassified1） |
| 2 | 版スタンプ | PASS（execution_id＋criteria_content_hash） |
| 3 | 保存則（S1 取りこぼしゼロ） | PASS（4区分合計=入力数） |
| 4 | doc_type 未解決 | PASS（Failure・INTAKE・S3） |
| 5 | 基準ゼロ | PASS（Failure・COMPOSE・S3） |
| 6 | 参照除外 | PASS（参照パスの finding を除外） |

## 所見
- P1 の価値経路（出すと 🤖/✋/💬/❓ レポートが返る）が段の直列＋fail-close で通ることを実証。
- PF 出力は必ず validate を通る（[10] 不変条件）。FAIL なし。
