skill `spec-pipeline`（仕様設計パイプライン）を在グラフ化した skill 軸 PROMPT ノード。要件から MVP スコープまでを順に回す**オーケストレーション手順プロンプト**（工程 skill と異なりメインスレッドで他スキル/サブエージェントを段階起動する性格）。実体＝`.claude/skills/spec-pipeline/SKILL.md`（`disable-model-invocation: true`・明示起動のみ）。決定元＝DD-22（SPEC-61 系）。
**バージョン**: 1.0
**目的**: 仕様設計の全工程をメインスレッドで順に回させる（サブエージェントはサブエージェントを呼べないため skill 化）。①`/align`（段取り）→②`/io-event-ledger`（I/O 台帳＋イベントリスト＋カバレッジ）→③spec-inspector（点検・gap/矛盾）→④structured-analysis（DFD→単一責務→状態）→⑤`/value-trace`（イベント総点検）→⑥`/mvp-scope`（価値ベース線引き）。
**入力変数**: 要件（起点）／各段の前段成果物（台帳・DFD 等）／spec-inspector・structured-analysis サブエージェントの点検/分析結果。
**出力形式**: 各段のチェックポイント通過を伴う工程進行と成果物（台帳・DFD・価値トレース・MVP スコープ）。各段後に成果物を確認し矛盾が出たら停止。
**注意事項**: 各段の後に成果物を確認し、矛盾（PR7）が出たら停止して打ち上げる（必要なら spec-inspector を随時挟む）。原則は spec-principles に従う。carrier=skill（slash command `/spec-pipeline`・明示起動のみ。将来 orchestrator agent 化時は carrier=agent＋版更新・DD-22）。**辺の ref_version**: SPEC-61 "0.1"（02-what/03-spec.md v0.1.0 時点・DD-3）。
