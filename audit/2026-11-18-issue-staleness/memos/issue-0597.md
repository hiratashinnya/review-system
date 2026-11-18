# Issue #597「主文脈の作業ディレクトリがサブディレクトリに移ると、agent-command-gate.sh が import に失敗して全 Bash を拒否し、自力で戻れなくなる」

- URL: https://github.com/hiratashinnya/review-system/issues/597
- 状態: closed（2026-11-18取得）
- 本文: 2153文字/ 51行。全文: `../raw/issues-2026-10.jsonl`
- AC: 3件（未チェック: 3）
- Issue参照: #586, #585, #340
- PR参照: #586
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## 再現手順 | ## 期待結果 / 実際結果 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues | ## Project fields（実行環境の制約により自動設定できず・要手動設定）
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - `.claude/hooks/agent-command-gate.sh` の埋め込み python は `sys.path.insert(0, os.getcwd())` の後に `from issue_start.gated_roles import GATED_ROLES` を行う。コメントは「フック実行時の cwd は常にプロジェクトルートに固定される」と前提しているが、主文脈（gated でないロール）は `cwd` を自由に変えられるため前
- - 同じ前提を持つ他のフック（`pr-merge-gate.sh` 等）があれば同様に確認する
- - [ ] 同じ前提を持つ他フックの確認結果が PR に記録されている
- - 関連：#340（内部例外時の fail-open を fail-close にした件）

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
