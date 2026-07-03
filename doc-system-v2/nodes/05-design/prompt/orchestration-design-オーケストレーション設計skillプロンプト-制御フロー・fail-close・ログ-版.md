skill `orchestration-design`（制御フロー・fail-close・ログ/版）を在グラフ化した skill 軸 PROMPT ノード。モジュール構成を端から端の実行（スイムレーンフローチャート）として固めるプロンプト。実体＝`.claude/skills/orchestration-design/SKILL.md`。決定元＝DD-22（SPEC-61 系）。
**バージョン**: 1.0
**目的**: レーン（外部アクタ＋層）を決め、各段が `Result` を返す直列を並べ、実行順序の不変条件（検証→…→副作用）を型で強制し、良性 no-op と異常を分け、ログのチャネル分離と版スタンプ（`MAJOR.MINOR`）を設計させる。失敗は下流を走らせず出口へ伝播（fail-close・PR6 価値経路を遮断しない・PR2 機構＝fail-close）。
**入力変数**: 物理アーキテクチャ（architecture-design のモジュール・ポート・IF）／失敗の型（`Result`/`StageOutcome`・domain-model）／安定化策（fail-close・トランザクション・版スタンプ・要件 S# 一覧）。
**出力形式**: スイムレーン flowchart（mermaid `subgraph`）＋実行順序の不変条件リスト＋`run_*()` 疑似コード（`match` で成功/失敗を漏れなく分岐）＋ログ3チャネル表＋版スタンプ定義。
**注意事項**: fail-close は横断経路（全段に効く error 経路）で、失敗も黙って空にせず明示通知。外部（LLM 等）出力は必ず検証段を通す（飛ばす経路を作らない）。制御チャネルを診断で汚さない。版は `MAJOR.MINOR`（MAJOR＝構造/型→対応ロジック改修・MINOR＝内容のみ）。シーケンス図は使わない。carrier=skill（slash command `/orchestration-design`・DD-22）。**辺の ref_version**: SPEC-61 "0.1"（02-what/03-spec.md v0.1.0 時点・DD-3）。
