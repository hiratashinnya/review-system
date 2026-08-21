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
