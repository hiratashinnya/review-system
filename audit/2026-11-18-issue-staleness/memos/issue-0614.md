# Issue #614「karte check が是正担当に渡らない finding（申し送り済みの harm: none、主文脈が処置する fix-here）で必ず NG になる」

- URL: https://github.com/hiratashinnya/review-system/issues/614
- 状態: closed（2026-11-18取得）
- 本文: 4641文字/ 89行。全文: `../raw/issues-2026-10.jsonl`
- AC: 4件（未チェック: 0）
- Issue参照: #604, #503, #538, #609, #603, #850, #495, #330, #691, #785, #683, #733
- PR参照: #604, #850, #733
- 主見出し: ## 目的・背景 | ## 現状と根拠（実測・2026-10-11・Issue #538 是正ラウンド1） | ## 意図した設計かどうか（1について・要確認） | ## Scope | ## Out of scope | ## Acceptance criteria | ### AC最終照合（2026-11-16 / PR #850 HEAD `bcbdeb4`） | ## Dependencies / Related issues | ## 【申し送り】#691 レビュー指摘の自動仕分け・Advisory台帳（2026-10-31） | ## 【申し送り・2026-11-07】#691 Release 2（#785）のKarte述語整合 | ## 【着手前申し送り・PR #733 / 2026-11-14】 | ### 診断要否（L5）
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- ## 現状と根拠（実測・2026-10-11・Issue #538 是正ラウンド1）
- - AC3: `test_issue_538_round_one_mixed_assignment` で #538 round 1 相当の混合ケースを再現し、`check` EXIT_OK / `status` harmful-open を検証。実際の #538 一時カルテの実行ではなく相当構成の回帰。
- - PRのマージまではIssue openとする。
- - **実装時の扱い**：双方の最新仕様・機械ゲート・テストを突き合わせ、既存契約を覆す変更は理由とオーナー承認を記録する。正式なGitHub relation/blocked-by設定は、本追記とは別に確定する。
- - #785「trusted自動仕分け確定とadvisory判定・STOP整合」は別Issueであり、現在の実装やACへ後出ししない。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
