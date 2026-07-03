skill `impl-design-pipeline`（実装設計パイプライン・spec→実装の橋渡し）を在グラフ化した skill 軸 PROMPT ノード。仕様確定後・実装前に固める凍結セットを順に回す**オーケストレーション手順プロンプト**。実体＝`.claude/skills/impl-design-pipeline/SKILL.md`（`disable-model-invocation: true`・明示起動のみ）。決定元＝DD-22（SPEC-61 系）。
**バージョン**: 1.0
**目的**: 論理 DFD＋ドメインモデル確定後に、実装前の凍結セットをチェックポイント付きで順に固めさせる。①凍結セット索引を立てる→②architecture-design→③orchestration-design→④prompt-design→⑤test-strategy 適用→⑥spec-inspector 総点検（G#）→⑦判断ログ DD# 記録。
**入力変数**: 確定した structured-analysis（論理 DFD・状態）と domain-model（型）／必要なら schema-design（外部形式）／新規資産があれば asset-auditor 点検結果。
**出力形式**: 設計索引（凍結セット）＋architecture/orchestration/prompt 各設計＋判断ログ（DD#）＋spec-inspector の G# 反映。同期更新＝method-inventory・asset-plan・CLAUDE.md。
**注意事項**: 実装設計フェーズは暫定で進めてよい（迷いは推奨案で暫定決定し DD# に記録して前進・空で止めない）。矛盾・オーナー判断必須は原案・比較・推奨を添えて止める。新規資産前に asset-auditor（A14）。各段は前段の確定物に接続（依存順を守る）。carrier=skill（slash command `/impl-design-pipeline`・明示起動のみ・DD-22）。**辺の ref_version**: SPEC-61 "0.1"（02-what/03-spec.md v0.1.0 時点・DD-3）。
