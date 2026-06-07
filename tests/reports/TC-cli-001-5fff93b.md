---
id: TC-cli-001
version: 1.0
---
# テスト成績書 — CLI／HTMLレポート（TC-cli-001）

ケース：`reviewer version` と `review`→HTML の通し。FakePlatform で決定化。

## ヘッダ
| 項目 | 値 |
|---|---|
| 対応ケース版 | 1.0 |
| 実装 commit id | `5fff93b` |
| prompt_template_version | review:3.1 |
| 実行日時 | 2026-06-07 |
| 環境 | Python 3.11.15・標準ライブラリのみ |
| ログ | [./../logs/TC-cli-001-5fff93b.txt](../logs/TC-cli-001-5fff93b.txt) |

## 結果：PASS（4/4）
- `version`：parsing/prompts の版定数（criteria/policy MAJOR・review:3.1 等）を表示。
- `review`：基準/ポリシーをファイルから読み→P1 通し→HTML を out に生成（exit 0）。
- `--type` 無し→exit 2（境界・MVP は AI 型推定なし）。
- HTML（DD10）：`data-review-id` 埋込・finding id・`class="decision"` チェック・`.feedback.json` 書き出し JS（DD14）。

## 実起動確認（手動・smoke）
`python -m review_system version` / `python -m review_system review a.py --type code --criteria … --out report.html` が実際に動作し、review_id 入り HTML を生成。

## 所見
- MVP P1 が**実 CLI から end-to-end で動く**ことを確認。実 PF アダプタ（ClaudeCode/stdout 駆動）と git 適用(P2)は残。FAIL なし。
