# 設計フェーズ index — 凍結セット（doc-system）

> spec-inspector 実装着手前に固める設計物。分析層（`03-analysis/`）の確定を前提とする。
> **設計フェーズ開始**: 2026-06-16（N2・analysis 確定済み）

## 凍結セット（着手順）

| # | 項目 | 成果物 | 状態 |
|---|---|---|---|
| A | モジュール/パッケージ構成・FileSystemPort | [01-modules](01-modules.md) | ✅ 著作済み（MOD-1〜12, PORT-1） |
| C | 永続層（DS1〜3・PRS1） | [02-persistence](02-persistence.md) | ✅ 著作済み（DS-1〜3, PRS-1） |
| ① | オーケストレーション（スイムレーン付きフローチャート） | [03-orchestration](03-orchestration.md) | ✅ 著作済み（ORC-1） |
| ③ | プロンプト設計 | 不要（LLM なし） | ➖ スキップ |
| ④ | テスト戦略 | `tests/`（証跡・sprint-2 以降） | ⬜ 未着手 |
| D | ロギング規約 | 検査パイプライン stdout のみ・O-1/O-2/O-6 にて確定 | ⬜ 未着手 |

> **② 外部アクタ IF**: CLI サブコマンドシグネチャ（`python -m spec_inspector [options]`）は ORC-1 本文に概要を記載。
> **判断ログ**: [DD-13/DD-14](../04-verification/04-decisions.md)（MOD 粒度・FileSystemPort 粒度）

## 依存規則（1枚）

```
domain ← ports ← core（config/collector/parser/checker/filter/coverage/reporter）
       ← adapters ← __main__（合成ルート）
```
- `core/*` は `domain.*` と `ports.*` だけに依存
- `adapters/*` が `ports.*` を実装（結線は `__main__` のみ）
