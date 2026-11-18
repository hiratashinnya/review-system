# Issue #222「design(hooks): agent-command-gate の producer/passthrough 追跡をfail-closedへ設計転換（whack-a-mole再発防止・#220統合）」

- URL: https://github.com/hiratashinnya/review-system/issues/222
- 状態: closed（2026-11-18取得）
- 本文: 2555文字/ 38行。全文: `../raw/issues-2026-07a.jsonl`
- AC: 0件（未チェック: 0）
- Issue参照: #219, #218, #220
- PR参照: #219
- 主見出し: ## 経緯（PR #219・3ラウンドにわたる whack-a-mole の記録） | ## 根本原因 | ## 決定（オーナー承認・2026-07-12） | ## スコープ | ## 受け入れ基準
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- 2. **2回目**：クラスA/B是正後、今度は**その是正コード自体**（`classify_operator_sequence_stage()`）を突く新規バイパス5件（`(cat && cat)`/`(cat; cat)`/`(cat 2>/dev/null)`等）を発見。加えて「安全側」というコメントが事実誤認（実際はfail-open）だったと判明。
- `.claude/hooks/agent-command-gate.sh`（Codexミラー同様）の producer/passthrough 追跡ロジック（`literal_producer_value_through_passthrough`・`classify_passthrough_stage`・`classify_subshell_body`・`classify_operator_sequence_stage`等）は、**「パイプ段が安全なpas
- **選択肢B：fail-closedへの設計転換**を採用。「passthroughと積極的に確定できないステージに遭遇したら、そこでpayloadがinterpreterへ到達しうるとみなしdeny側に倒す」という前提に反転する。
- - 選択肢C（現状受容）：ゲートは多層防御の一枚と割り切り残存ギャップとして文書化するのみ。fail-open構造そのものは温存されるため不採用。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
