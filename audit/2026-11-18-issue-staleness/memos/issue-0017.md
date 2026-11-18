# Issue #17「docs(lateral-deploy): extract_spec_principles の spec-principles 依存をコメントで明記」

- URL: https://github.com/hiratashinnya/review-system/issues/17
- 状態: closed
- 本文: 860文字、29行。全文スナップショット: `../raw/issues-2026-06.jsonl`
- AC: 総0、未チェック0（本文のチェックボックス表記に限る）
- 関連番号: Issues #13 / PRs #13
- 主見出し: ## 背景 | ## 対応案 | ## 参考
- 判定（一次）: E（Closed：履歴保全。現在の運用指示には使わず）

## 本文中の状態・依存記述（最大7件）
- `extract_spec_principles()` は `"PR1" in line` / `"PR2" in line` / `"PR3" in line` をトリガーに原則セクションの抽出を開始し、`---` で終了、50行上限で打ち切るヒューリスティックになっている。現状の `.claude/skills/spec-principles/SKILL.md` 構成では正しく動作するが、以下

## 点検メモ
- 本文全体を文字列走査し、AC・状態断言・参照関係を抽出。引用時点の歴史的記述を現行事実と取り違えない。
- 関連Issue／PRの最新状態と実コードとの突合は横断工程で行う。未実施の検証を合格扱いしない。
