# GitHub Copilot 固有 guidance

この節は GitHub Copilot の loader と利用可能資産を記録する。共通の規範は直前の共通 guidance を正とする。

## PR7 の Copilot 実行契約

- 仕様設計・点検中の矛盾は、共通 guidance の PR7 にある ①Q/FND ノード起票、②対象ダッシュボード更新、③原案・比較・理由付き推奨を添えて停止、の順を省略しない。チャットだけで停止しない。
- ノード著作は利用可能な `verification-author`、検証・反映は `reconciliation-validator` → `reconciliation` を使う。これは Copilot で共通の意味を実行するための能力対応であり、Claude／Codex 固有の hook、command gate、worktree を持ち込まない。

## Skills（用途に応じて自動選択）

| Skill | 用途 |
|---|---|
| `align` | 着手前の認識合わせ |
| `value-trace` | イベントから出力までの価値経路・DFD レベリング検証 |
| `mvp-scope` | 価値ベースの MVP スコープ決定 |
| `schema-design` | 外部設定・基準ファイルのスキーマ設計 |
| `domain-model` | データ辞書から型安全なドメインモデルを導出 |
| `architecture-design` | 論理 DFD とドメインモデルから物理アーキテクチャを設計 |
| `orchestration-design` | runtime 制御フローを設計 |
| `prompt-design` | LLM システムプロンプトを設計 |
| `test-strategy` | review-system のテスト戦略 |
| `bloom-model-tier` | Bloom 分類で agent の model tier を選定 |
| `docidx` | v1 archive 専用ノード検索 |
| `coverage-html` | unittest と coverage HTML の確認 |
| `issue-pipeline` | Issue 実装から close までの進行管理。専用 Agent がない工程は利用可能な実行手段へ読み替え、役割分担・順序・STOP 契約は維持する |

## Prompts（ユーザーが `/` で明示起動）

- `/asset-lateral-deploy`: PF 間の資産移植
- `/asset-pipeline`: 手法から skill／agent への資産化
- `/impl-design-pipeline`: 実装設計の凍結セット作成
- `/spec-pipeline`: 要件から MVP scope までの仕様設計

## Agents

- ノード著作: `requirements-author`、`spec-author`、`analysis-author`、`design-author`、`verification-author`
- 一括著作: `authoring-fanout`
- 検証・反映: `reconciliation-validator` → `reconciliation`
- 点検・分析: `spec-inspector`、`structured-analysis`、`asset-auditor`
- ノード検索: `dsv2-lookup`
- 設定操作: `doc-system-config-operator`
- 共通参照: `doc-system-v2-authoring`（単独起動しない）

## Copilot 固有の非移植

- `/agy-delegate`、`/codex-review`、`/gh-create-issue` はローカル CLI、認証、対象 PF の明示スコープに依存するため移植しない。
- `issue-implementer`、`issue-fixer`、`pr-reviewer` の Copilot Agent 版は、project hook、worktree bind、ロール別 command gate の等価物がないため配置しない。
- Copilot は Prompt の明示起動と Agent の選択・委譲を使い、Claude／Codex 固有の hook や worktree 実行機構を持ち込まない。
