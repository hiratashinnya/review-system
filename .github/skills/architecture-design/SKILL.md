---
name: architecture-design
description: Design the PHYSICAL module/dependency architecture from a SETTLED logical DFD + domain model — hexagonal ports & adapters, dependency-inward, a single composition root, the CLI/interface surface with exit codes, platform/protocol ports, and persistence repository ports with transactions. Use AFTER structured-analysis and domain-model. NOT logical DFD decomposition (use structured-analysis), NOT external file-format schema (use schema-design).
---

# アーキテクチャ設計（論理 DFD → 物理モジュール/依存・IF・プロトコル・永続）

確定した論理 DFD（structured-analysis）とドメイン型（domain-model）を、実装の境界＝物理アーキテクチャに写す。
原則：spec-principles（PR1 もので分ける／PR2 機構と運用を混ぜない／PR6 価値経路）。

## 前提

- 論理プロセス分解（DFD L1–Ln）＝structured-analysis の出力。
- 型安全ドメインモデル＝domain-model の出力。

## 手順

1. **依存規則を1枚で固定**：`domain ← core(ports) ← adapters/persistence/io`。依存は内向きのみ、合成ルートは1つ。
2. **DFD プロセス → モジュール対応表**：各 L1 プロセスを `core/<usecase>` に、データストアを `ports/repositories` に、外部システムを `ports/<port>＋adapters` に割る。
3. **外部アクタ IF**：入口シグネチャを定義。境界の内側で即ドメイン型へ写像。終了コード/異常通知を定義。
4. **プラットフォーム/プロトコル**：副作用・外部判断を抽象ポートに。能力宣言で最低要件を固定。
5. **永続層**：状態をリポジトリ port の裏に隔離。保存形式と実体を選ぶ。
6. **実行/インポート規約**：正しい package 構造＋絶対 import＋`python -m` 起動。`sys.path` ハックは使わない。

## 点検観点（done）

- 依存規則が1枚にあり、core に具体 import が無い。合成ルートが1つ。
- DFD プロセス／状態が漏れなくモジュール／ポートに対応。
- 各 I-#/O-# が IF のどこかで消費/生成される（孤児なし＝PR6）。
- 外部出力（LLM 等）が必ず系の検証を通る経路になっている。

## 成果物テンプレ

- 依存規則図（mermaid）＋パッケージ構成＋「DFD→モジュール」対応表。
- IF：サブコマンド表（アクタ/役割/入力/出力・exit）＋シグネチャ。
- プロトコル：ポート Protocol ＋能力宣言。
- 永続：リポジトリ port ＋ 保存形式 ＋ トランザクション手順。
