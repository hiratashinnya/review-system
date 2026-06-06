# CLAUDE.md — 作業規約

このリポジトリでの仕様策定・設計の進め方。手法の棚卸しは `docs/methods/method-inventory.md`、
スキル/エージェントの計画は `docs/methods/asset-plan.md`、実体は `.claude/`。

## 迷ったら原則に戻る
判断は **spec-principles（PR1–PR10）**（`.claude/skills/spec-principles/`）に従う。特に：
**もの＋発生源で分ける**／**機械判定と運用ルールを混ぜない**／**価値経路を遮断しない**／
**矛盾は停止して打ち上げ**／**系外＝非イベント**／**観測できないものは持たない**。

## 決定ダッシュボード運用（A2）
- 未決は `docs/dashboard.md` に Q# として起票し、状態（未決/方針あり/確定/クローズ）を維持。
- 決定は「決定済み」へ。削除はクローズで**理由を残す**（消さない＝PR8）。
- 確定は本文（台帳/設計）に反映し、削除済み項目の生き残り参照を Grep で確認。

## 案出し（A3）
- 論点は1文化 → 2–4 の排他的選択肢＋トレードオフ → 推奨＋根拠 → Q# に記録。
- 運用ルール（PR2）は機構＋デフォルトに留め、設計で詰めない。

## スキル/エージェント
- スキル：`/align` `/io-event-ledger` `/value-trace` `/mvp-scope` `/schema-design` `/spec-pipeline` `/asset-pipeline`
- サブエージェント：`spec-inspector`（仕様点検）・`structured-analysis`（DFD 分解）・`asset-auditor`（資産の重複/矛盾/競合監査・read-only）
- **新しいスキル/エージェント/コードを作る前に `asset-auditor` で重複/競合を点検**し、新規 vs 既存変更を判断（A14）。
- 初回は `.claude/` のワークスペース信頼を受諾する必要がある。

## このリポジトリ
- 現状ドキュメント中心（要件・設計フェーズ）。実装は Python/ML スタック想定。
- MVP ターゲットは `docs/dashboard.md`（P1＋P2）と `docs/requirements/12-mvp-scope.md`。
