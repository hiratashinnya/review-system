---
id: TC-repo-001
version: 1.0
---
# テスト成績書 — 基準/ポリシーローダ（TC-repo-001）

ケース：tmp に criteria(.md)/policy(.yaml) を書き、ローダで読む。Q24=A のパーサ拡張に依存。

## ヘッダ
| 項目 | 値 |
|---|---|
| 対応ケース版 | 1.0 |
| 実装 commit id | `a55cf07` |
| 実行日時 | 2026-06-07 |
| 環境 | Python 3.11.15・標準ライブラリのみ |
| ログ | [./../logs/TC-repo-001-a55cf07.txt](../logs/TC-repo-001-a55cf07.txt) |

## 結果：PASS（4/4）
- criteria .md → ComposedRule（メタ：determinism/severity/override/enabled・provenance=org）。
- 本文 `## <id> — <title>` セクションを guidance.summary に抽出。
- policy .yaml → PolicyMatrix（det→{"*":mode}）。override が最優先で解決。
- discover_criteria が doc_type でフィルタ（不一致は拾わない）。

## 所見
- 矛盾 Q24 をオーナー決定(A)どおりパーサ拡張で解消。**文法を先に schema に明文化してから**実装（schema の自己ルール遵守）。FAIL なし。
