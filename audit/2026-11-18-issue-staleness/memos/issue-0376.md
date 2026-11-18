# Issue #376「バックログのバッチ棚卸し運用を定める（オーナー処分のスループット向上）」

- URL: https://github.com/hiratashinnya/review-system/issues/376
- 状態: open（2026-11-18取得）
- 本文: 4562文字/ 127行。全文: `../raw/issues-2026-08b.jsonl`
- AC: 8件（未チェック: 8）
- Issue参照: #371, #261, #263, #264, #265, #108, #372, #375, #370, #368, #405, #406, #407, #691, #786, #782, #524
- PR参照: なし
- 主見出し: ## 棚卸し提示形式への追加 | ### Acceptance criteria追加 | ## 目的・背景 | ## 現状と根拠 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues | ## Project fields（実行環境の制約により自動設定できず・要手動設定） | ## 【追記】前提変化の申し送り（Claude Code (AI)・2026-09-05・Issue #405 全オープンIssue影響点検） | ## 【申し送り】#691 レビュー指摘の自動仕分け・Advisory台帳（2026-10-31） | ## 【申し送り・2026-11-07】#691 / #786 Advisory棚卸しの接続
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- - open Issue **65件**（2026-08-16 時点）。うち21件は直近15日に起票されたもの。
- ## 【追記】前提変化の申し送り（Claude Code (AI)・2026-09-05・Issue #405 全オープンIssue影響点検）
- - **変更点**：Scope「バックログ棚卸しの運用を定義し、`/issue-pipeline` SKILL.md（または独立した運用文書）に記載する」の対象、および「現状と根拠」が引用する `.claude/skills/issue-pipeline/SKILL.md` ④の本文は `.ai/skills/issue-pipeline/SKILL.md` に移動している。`.claude/` 側は現在 frontmatter とリンクだけの wrapp
- 対応要否・実施時期はオーナー判断（本追記は前提変化の記録のみで、対応不要とは判断していない）。
- - **実装時の扱い**：双方の最新仕様・機械ゲート・テストを突き合わせ、既存契約を覆す変更は理由とオーナー承認を記録する。正式なGitHub relation/blocked-by設定は、本追記とは別に確定する。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
