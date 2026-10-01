# doc-eval（仮称）

> **D-001 — リポジトリの目的**
>
> 本リポジトリの目的は、オーナーが AI 駆動開発のノウハウを獲得すること。review_system はその題材であって目的ではない。製品の進捗はこのリポジトリの成功指標ではない。ハーネスを作り込んで品質・進捗・コストを改善すること、およびアンチパターンを経験すること自体に価値がある。獲得したノウハウの転用先は車載 ECU であり、品質担保はマストである。

社内のあらゆる文書（プログラム / 仕様書 / 議事録 など）の評価を、AI により
**効率化** し **品質を均質化** するための社内ツール。

## 解決したい課題

- 人手レビューに時間がかかる
- 評価基準がレビュアーごとにバラバラで、品質にムラがある

## 提供価値

- **効率化** — レビュー工数の大幅削減
- **均質化** — 文書タイプ・レビュアーによらない一貫した品質
- **組織学習** — 評価基準が使うほど育ち、ナレッジとして蓄積される

## ドキュメント

| ファイル | 内容 |
|---|---|
| [docs/dashboard.md](docs/dashboard.md) | 未決事項・ネクストアクション（運用ハブ） |
| [docs/requirements/00-overview.md](docs/requirements/00-overview.md) | 要件 全体像 |
| [docs/requirements/01-criteria-files.md](docs/requirements/01-criteria-files.md) | 評価基準ファイル |
| [docs/requirements/02-evaluation-and-triage.md](docs/requirements/02-evaluation-and-triage.md) | 評価実行と指摘の仕分け |
| [docs/requirements/03-auto-fix-policy.md](docs/requirements/03-auto-fix-policy.md) | 自動修正ポリシー |
| [docs/requirements/04-feedback-loop.md](docs/requirements/04-feedback-loop.md) | フィードバックループ（基準育成） |
| [docs/minutes/](docs/minutes/) | 議事録 |

## ステータス

要件定義フェーズ（壁打ち中）。技術スタック・MVP の線引きは未着手。
