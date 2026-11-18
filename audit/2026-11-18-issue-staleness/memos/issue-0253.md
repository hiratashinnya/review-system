# Issue #253「必須辺検証ルールの見直し・修正（①scm←cfg）」

- URL: https://github.com/hiratashinnya/review-system/issues/253
- 状態: open（2026-11-18取得）
- 本文: 6275文字/ 145行。全文: `../raw/issues-2026-07b.jsonl`
- AC: 8件（未チェック: 8）
- Issue参照: #160, #163
- PR参照: なし
- 主見出し: ## 調査結果の追記（Claude Code (AI) が調査・整理／2026-07-26） | ### 1. 現状の機械状態 | ### 2. 実測：SCM は 2種類ではなく **3種類** | ### 3. b の5件 → 張り替え先（実在ノードで確認済み） | ### 4. 規則の再設計案（Issue 本文の提案を具体化） | # doc-system-v2/schema/sidecar.schema.json（carrier と同じ enum 方式で判別属性を追加） | # doc-system-v2/config.yml | ### 5. 施行器の改修が1点必要 | ### 6. 作業手順（依存順） | ### 7. 受け入れ条件 | ### 8. オーナー判断が必要な点（着手前に確認） | ### 9. 関連
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- ### 1. 現状の機械状態
- | 分類 | 件数 | ノード | 現在の入辺 |
- 1. `carrier` — `doc-system-v2/schema/sidecar.schema.json` の enum が機械可読 SoT（値 `skill|agent|command|instructions|hooks|code`、現在 PROMPT 15件で使用）。「ノードYAMLのサブ属性 + vocab 配列」の既存実装パターン。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
