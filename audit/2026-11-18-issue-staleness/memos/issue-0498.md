# Issue #498「codex-cli 0.153.4 が features.* config override（特に unified_exec）を反映するか切り分ける」

- URL: https://github.com/hiratashinnya/review-system/issues/498
- 状態: closed（2026-11-18取得）
- 本文: 7246文字/ 101行。全文: `../raw/issues-2026-09.jsonl`
- AC: 7件（未チェック: 7）
- Issue参照: #491, #452
- PR参照: なし
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ### 実測（2026-09-07〜08・本作業環境） | ### 公式ドキュメント（developers.openai.com/codex・2026-09-08 時点） | ## 解く質問 | ## 調査境界 | ## Timebox | ## 意思決定となる成果物 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- > **2026-09-08 追記・本文訂正（Claude Code (AI)）**：初版は「override が反映されていない。つまり GA 化して flag では切れなくなったのか」と、未確認の推測を確定事実のように書いていた。公式ドキュメント（developers.openai.com/codex）を確認したところ `unified_exec` は Stable かつ `[features]` で無効化可能と明記されており、初版の記述はドキュメント
- `issue_start/codex_supervisor.py` の supervised Codex 起動は、内側 Codex に broker 以外の汎用 process 実行能力を持たせないことを隔離の前提としている。`build_codex_command` は `--config features.<name>=false` 群でこれを無効化する。**導入済み codex-cli 0.153.4 では、同じ overrides を渡しても `c
- これは公式ドキュメントの記載と矛盾する。ドキュメント（下記「現状と根拠」に引用）では `unified_exec` は Stable / default `true`（Windows 以外）で、`[features]` テーブルまたは `--config features.unified_exec=false`（precedence 最上位）で無効化できるとされている。**無効化不能とも GA 固定とも書かれていない。**
- ### 公式ドキュメント（developers.openai.com/codex・2026-09-08 時点）
- 4. `unified_exec` が supervised 構成で実際に有効なままなら、その PTY exec 能力は supervisor の bwrap / sandbox 層で封じ込められているか（隔離が「前提」で終わっていないかの確認）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
