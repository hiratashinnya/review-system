# Issue #303「agent-command-gate.sh を context-mode 実行系MCPツール(ctx_execute/ctx_execute_file/ctx_batch_execute)に拡張する（ツール付与は含まない）」

- URL: https://github.com/hiratashinnya/review-system/issues/303
- 状態: closed（2026-11-18取得）
- 本文: 3329文字/ 57行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 4件（未チェック: 4）
- Issue参照: #274
- PR参照: なし
- 主見出し: ## 背景 | ## 実装内容 | ### 1. `.claude/settings.json` — matcher拡張 | ### 2. `.claude/hooks/agent-command-gate.sh` — 入力正規化＋判定 | ### 3. 判定方針 | ### 4. テスト（`tests/unit/test_agent_command_gate.py`） | ## 受け入れ条件 | ## スコープ外（別Issueに分離・オーナー指示） | ## 参照
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- #274 で、context-mode の実行系MCPツール（`ctx_execute`/`ctx_execute_file`/`ctx_batch_execute`）を解禁する前提として、`.claude/hooks/agent-command-gate.sh` が担保している統制（役割別push/merge非対称・危険コマンドdeny）をこれらのツールにも拡張する設計を確定した。詳細な調査結果は #274 のコメントを参照。
- - **未知のMCPツール名・入力形が読めない呼び出しは全ロールでfail-close（deny）**。Bash側の非ゲートロールfail-open（既存ワークフロー救済のための例外）とは意図的に非対称にする。
- - **ツール付与（解禁）**：本Issueにblocked byの別Issueで実施（ゲートが安定してから付与、の順序をIssue依存関係で強制する）
- - **Codex側 (`.codex/hooks/agent-command-gate.sh`) への移植**：本Issueにblocked byの別Issueで実施

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
