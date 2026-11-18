# Issue #492「.claude/rules/02-decision-process.md の汎用ハーネス列挙が実在ツールに追随しておらず、起票先を判定表から引けない」

- URL: https://github.com/hiratashinnya/review-system/issues/492
- 状態: closed（2026-11-18取得）
- 本文: 3733文字/ 80行。全文: `../raw/issues-2026-09.jsonl`
- AC: 5件（未チェック: 5）
- Issue参照: #490, #488, #431
- PR参照: #490
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## 影響 | ## 提案挙動 | ## Scope | ## Out of scope | ## 互換性 | ## 代替案 | ## Acceptance criteria | ## Dependencies / Related issues | ## Project fields（未設定項目・手動設定が必要）
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - `CLAUDE.md` は本ファイルを `@` import して毎ターン配送しており、列挙は「現在有効な恒常規範」として扱われる。実態とずれた列挙が規範として配られ続ける。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
