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

## 判断の仰ぎ方（フェーズ別・空で止めない＝PR7）
- **大原則**：矛盾・オーナー判断必須で止めるときも、**原案・比較・理由付き推奨/非推奨を必ず添える**（意見なき停止は禁止）。**矛盾は原案検討して提案、他のやれる所をやる、一通り終えたら整理して提示**。
- **起票してから止める（チャットで流さない）**：論点・矛盾・情報不足を見つけたら、**①起票 → ②ダッシュボード更新 → ③選択肢＋推奨を添えて停止・質問** の順を必ず守る。チャットで指摘を述べるだけで**起票しないのは禁止**（後から「なぜ起票してない？」になる）。
  - **起票先の使い分け**：未決の論点・選択肢＝**Q#**（ダッシュボード）／**既存ノードに対して発見した指摘・矛盾・原則違反＝FND**（[verification](doc-system/04-verification/02-findings.md) 等・`verification-author` に委譲）。どちらも本文に内容・深刻度・推奨を書き、ID だけで投げず**本文で説明してから判断を仰ぐ**。
  - **処置したら必ずバックリファレンス**：FND を resolved にしたら処置対象ノードに `→FND-x` 辺を付与（削除済みノードは FND 本文に「付与先なし」と明記）。
- **要件定義フェーズ**：**暫定で進めない（危険）**。論点・矛盾・情報不足は**上記①〜③で止めて**選択肢＋推奨を出し、決定はオーナー。**他の決められる所を先に進める**（Q#/FND で起票・状態維持）。
- **設計フェーズ**：迷いは**推奨案で暫定決定**し、**判断ログ DD#**（論点→選択肢→推奨→暫定決定→影響範囲）に記録して前進。覆る場合の影響範囲を必ず併記。
- **DD# は Q# の設計フェーズ版**：未決の置き場が Q#（ダッシュボード）、暫定決定の記録が DD#（[design/decisions](docs/design/decisions.md)）。

## スキル/エージェント
- スキル（仕様）：`/align` `/value-trace` `/mvp-scope` `/schema-design` `/domain-model` `/spec-pipeline` `/asset-pipeline`
- スキル（実装設計）：`/architecture-design` `/orchestration-design` `/prompt-design` `/impl-design-pipeline`（凍結セット）・`/test-strategy`
- サブエージェント（点検・分析）：`spec-inspector`（仕様点検）・`structured-analysis`（DFD 分解）・`asset-auditor`（資産の重複/矛盾/競合監査・read-only）
- サブエージェント（著作・調停）：`requirements-author`・`spec-author`・`analysis-author`・`design-author`・`verification-author`・`reconciliation`
- **新しいスキル/エージェント/コードを作る前に `asset-auditor` で重複/競合を点検**し、新規 vs 既存変更を判断（A14）。
- 初回は `.claude/` のワークスペース信頼を受諾する必要がある。

## ノード著作の委譲ルール
ノードを著作するときは必ず対応するサブエージェントに委譲する（主文脈で直接書かない）：
- **VAL / SR / FR / NFR** → `requirements-author`
- **SPEC** → `spec-author`（1アサーション1ノード・-N枝番・無名依存辺で親 SPEC を参照）
- **ACTOR / I / O / D / P / E** → `analysis-author`
- **ORC / DS / MOD / DM / PORT / PRS / SCM / CFG / PROMPT / TERM** → `design-author`
- **TD / TC / TR / VERIFY / FND / DD / Q / PEND** → `verification-author`
- **著作後の整合確認・本ファイル確定書き込み** → `reconciliation`

各著作エージェントは `tmp/<sprint>/<parent-id>.md` に出力する。`reconciliation` が検証後に本ファイルへ反映する。

## 資産のテーラリング運用（A16）
- プロセスはスキル等で実現するため、**テーラリングの実体は `.claude/` に置く（docs ではない）**。
- 汎用標準は `.claude/standards/<name>/`（**非活性・auto-load されない**）、テーラリング済 active は `.claude/skills/<name>/`、対応は `.claude/tailoring-registry.md`。
- テーラリング時は**元（汎用標準）を `git mv` で `standards/` へ移動・非活性化**（消さない＝PR8）し、テーラリング版を `skills/` に置き、**registry に内容と実体パスを記録**。
- 初回適用＝`/test-strategy`（④ テスト戦略）。

## 実装設計フェーズ（凍結セット・判断ログ・A17–A20）
- 仕様確定後・実装着手前に **凍結セット**（モジュール／IF／プロトコル／永続／オーケストレーション／プロンプト／ログ・版／テスト戦略）を固める。索引＝`docs/design/README.md`。
- 手順は `/impl-design-pipeline`（`/architecture-design`→`/orchestration-design`→`/prompt-design`→`/test-strategy`）。**新規資産前に asset-auditor**（A14）。
- **判断ログ（DD#）**：仕様で一意に決まらない点は `docs/design/decisions.md` に `論点→選択肢→推奨→暫定決定→影響範囲` で記録（設計は暫定で前進・PR7）。
- **総点検（凍結セット規律）**：設計一式を **spec-inspector** に点検させ、G#（孤児/穴/分割違反/矛盾）を出して反映してから実装へ。
- **版は `MAJOR.MINOR`**（MAJOR=構造/型→対応ロジック改修・MINOR=内容のみ）。版↔対応ロジックを一目で追えること。

## このリポジトリ
- 現状ドキュメント中心（要件・設計フェーズ）。実装は **Python・原則標準ライブラリのみ**（Q5/Q5a：フロントマターも自前パーサ）。
- MVP ターゲットは `docs/dashboard.md`（P1＋P2）と `docs/requirements/12-mvp-scope.md`。
- 実装設計：データ辞書集約は `docs/design/00-data-dictionary.md`、型安全なドメインモデルは `docs/design/01-class-design.md`（`/domain-model`）。
- **実装前の凍結セット（8項目）**：索引＝`docs/design/README.md`。基盤＝`docs/design/02-module-architecture.md`。テスト戦略＝`/test-strategy`。
