# Issue #304「拡張済みゲートを前提に ctx_batch_execute / ctx_execute(shell) を対象ロールへ付与する（解禁）」

- URL: https://github.com/hiratashinnya/review-system/issues/304
- 状態: closed（2026-11-18取得）
- 本文: 1867文字/ 41行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 4件（未チェック: 4）
- Issue参照: #274
- PR参照: なし
- 主見出し: ## 背景 | ## 対象ロール（解禁マトリクス） | ## 実装内容 | ## ドッグフーディング検証（受け入れ条件に含める） | ## 受け入れ条件 | ## 参照
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- > 本 Issue は **Claude Code（AI）** が、オーナー指示に基づき #274 の調査結果を受けて起票した。**ゲート拡張が完了・merge済みであることを前提とするため、ゲート拡張Issueに blocked by を設定する**（付与が先行すると拡張前のゲートを素通りする状態が生まれるため）。
- ゲート拡張Issue（本Issueがblocked byとして参照するIssue）で `.claude/hooks/agent-command-gate.sh` が context-mode 実行系MCPツール（`ctx_execute`/`ctx_execute_file`/`ctx_batch_execute`）にも役割別の統制を適用できるようになった後、実際に対象ロールへツールを付与（解禁）する。
- - ゲート拡張Issue（blocked by）

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
