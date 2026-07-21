skill `architecture-design`（論理 DFD → 物理モジュール/依存・IF・プロトコル・永続）を在グラフ化した skill 軸 PROMPT ノード。確定した論理 DFD＋ドメイン型を ports & adapters の物理境界へ写すプロンプト。実体＝`.claude/skills/architecture-design/SKILL.md`。決定元＝DD-22（SPEC-61 系）。
**バージョン**: 1.0
**目的**: 依存規則（`domain ← core(ports) ← adapters/persistence/io`・内向きのみ・合成ルート1つ）を固定し、DFD プロセス→モジュール対応、外部アクタ IF（CLI シグネチャ＋終了コード）、プラットフォーム/プロトコル（抽象ポート＋駆動プロトコル＋能力宣言）、永続層（リポジトリ port＋保存形式）を設計させる（PR1 もので分ける・PR2 機構と運用を混ぜない・PR6 価値経路）。
**入力変数**: 確定した論理 DFD（L1–Ln・structured-analysis 出力）／型安全ドメインモデル（domain-model 出力）／外部ファイル形式が要る場合は schema-design 出力。
**出力形式**: 依存規則図（mermaid）＋パッケージ構成＋「DFD→モジュール」「状態→所在」対応表／サブコマンド表＋シグネチャ＋I/O 台帳対応／ポート Protocol＋能力宣言／リポジトリ port＋保存形式＋トランザクション手順。
**注意事項**: 依存は内向きのみ（core が adapters/io を import したら負け）。境界を跨ぐ値はドメイン型のみ・失敗は `Result`（fail-close を型で強制）。外部出力（LLM 等）は必ず系の検証を通す（直行経路を作らない）。`python -m` 起動・`sys.path` ハック禁止。DFD→モジュール粒度は孫プロセス有無＋責務圏で判断。carrier=skill（slash command `/architecture-design`・DD-22）。**辺の ref_version**: SPEC-61 "0.1"（02-what/03-spec.md v0.1.0 時点・DD-3）。
**FND-99（設計接続規則の非伝播）の backref 対象として在グラフ化**：本 PROMPT は接続規則を記述する out-of-graph 著作資産の在グラフ担体であり、FND-99 の処置対象として backref 辺を張る（→FND-99・指摘時 ref_version 0.1／fnd version 0.1.1 時点）。
