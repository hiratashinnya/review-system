# Issue #256「必須辺検証ルールの見直し・修正（④ implementation 段 src 系規則の対称化・担体/粒度適格性）」

- URL: https://github.com/hiratashinnya/review-system/issues/256
- 状態: open（2026-11-18取得）
- 本文: 6218文字/ 174行。全文: `../raw/issues-2026-07b.jsonl`
- AC: 7件（未チェック: 7）
- Issue参照: #160, #253, #118, #254, #255, #163
- PR参照: なし
- 主見出し: # 欠陥1: `must_link_to` と `must_be_linked_from` の非対称（最優先） | ## 実測（`doc-system-v2/config.yml`） | ## 何が起きるか | ## 経緯 | ## 選択肢 | ## 推奨 | # 欠陥2: `mod←src` の適格 kind が `module` 固定で、非 Python 担体の MOD を被覆できない | ## 背景 | ## 実測 | ## 既存資産 | ## 選択肢 | ## 推奨
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- **#160（SRC materialize）の前提となるブロッカー。本 Issue が閉じないと #160 は着手できない。**
- - **C: 現状維持** — #160 が着手不能のまま。
- `doc-system-v2/schema/sidecar.schema.json` の **`carrier` が既に enum で `skill|agent|command|instructions|hooks|code` を持つ**（「設計要素の実現担体」・現在 PROMPT 15件で使用）。これを MOD/PRS にも付与すれば判別できる。
- 一方 `src_symbol_eligibility: cfg: [file]` は**ファイル単位**。YAML キー単位の qualname 検証機構は現状存在しない（`validate.py:438 _python_qualnames()` は Python AST 専用）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
