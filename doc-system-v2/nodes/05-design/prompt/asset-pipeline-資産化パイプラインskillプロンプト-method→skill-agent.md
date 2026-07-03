skill `asset-pipeline`（資産化パイプライン・method → skill/agent/規約）を在グラフ化した skill 軸 PROMPT ノード。確立したメソッドを資産化する手順をメインスレッドで順に回す**オーケストレーション手順プロンプト**。実体＝`.claude/skills/asset-pipeline/SKILL.md`（`disable-model-invocation: true`・明示起動のみ）。決定元＝DD-22（SPEC-61 系）。
**バージョン**: 1.0
**目的**: メソッドの資産化をチェックポイント付きで順に回させる（サブエージェントはサブエージェントを呼べないため skill 化）。①棚卸し（対象活動をカード化・ユーザーの指摘/質問/課題提起を重点的に拾う・原則 PR と活動 A を分離）→②asset-auditor で重複/矛盾/競合を点検し新規 vs 既存変更を判断→③提案（振り分け＋汎用化前後の双方提示）→④形式適合確認（ターゲット仕様を一次確認）→⑤フェーズ毎の実体化（最小・最再利用単位から・台帳/プラン/規約を同期更新）→⑥検証（要否と方法・実施はユーザー確認）。
**入力変数**: 資産化対象の活動/メソッド（method-inventory の A#）／ユーザーの指摘・質問・課題提起／asset-auditor の重複/矛盾/競合点検結果／ターゲット（skill/agent/規約）仕様。
**出力形式**: カード化した棚卸し／振り分け提案（スキル/エージェント/共有リファレンス/規約・汎用前後）／実体化した資産＋台帳（tailoring-registry・method-inventory・asset-plan）同期更新／検証結果。
**注意事項**: 原則(PR)と活動(A)を分離。既存資産調査（asset-auditor）を必ず通し新規 vs 既存変更を判断（A14）。憶測で作らず形式適合を一次確認（原則を制約へ翻訳＝subagent は AskUserQuestion 不可→STOP 報告）。矛盾（PR7）は停止して打ち上げ。検証実施はユーザー確認を求める。carrier=skill（slash command `/asset-pipeline`・明示起動のみ・DD-22）。**辺の ref_version**: SPEC-61 "0.1"（02-what/03-spec.md v0.1.0 時点・DD-3）。
