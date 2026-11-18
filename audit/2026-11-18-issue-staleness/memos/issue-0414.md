# Issue #414「pr_merge_gate: merge成功後にPOST_AUDIT_INTEGRITY_ERROR/AuditErrorが発生する（監査ログ書き込み経路の不具合疑い）」

- URL: https://github.com/hiratashinnya/review-system/issues/414
- 状態: closed（2026-11-18取得）
- 本文: 2378文字/ 61行。全文: `../raw/issues-2026-08b.jsonl`
- AC: 3件（未チェック: 3）
- Issue参照: #413, #412
- PR参照: #413
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## Scope | ## Out of scope | ## Acceptance criteria | ## bug: 再現手順・期待結果・実際結果・環境・影響・root cause 仮説 | ## Dependencies / Related issues | ## Project fields（実行環境の制約により自動設定できず・要手動設定）
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - 再現手順：上記「現状と根拠」参照。`pr_merge_gate` フックが有効な状態で任意のPRを `gh pr merge` でマージする（PR #413で実際に発生）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
