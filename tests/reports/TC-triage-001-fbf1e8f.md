---
id: TC-triage-001
version: 1.0
---
# テスト成績書 — 検証・参照除外・仕分け（TC-triage-001）

ケース [TC-triage-001.md](../cases/TC-triage-001.md) のコピー＋実測。

## ヘッダ
| 項目 | 値 |
|---|---|
| 対応ケース版 | 1.0 |
| 実装 commit id | `fbf1e8f` |
| 実行日時 | 2026-06-07 |
| 環境 | Python 3.11.15・標準ライブラリのみ |
| ログ | [./../logs/TC-triage-001-fbf1e8f.txt](../logs/TC-triage-001-fbf1e8f.txt) |

## 結果：PASS（11/11）
- validate：既知=valid／未知=❓未分類（S1・crash なし）／保存則（valid+未分類=入力）。
- exclude_reference：参照集合のパスを除外／同名別ディレクトリは残す（エッジ）。
- triage：deterministic→AUTO・tradeoff→APPROVE・judgment→JUDGE。
- **S2 安全側**：メタ未宣言／matrix 欠落とも **🤖 を生まず HUMAN_ONLY**（境界）。override が mode を上書き。

## 所見
- S1「取りこぼしゼロ」・S2「確証なきは人へ」を境界で実証。FAIL なし。
