# Issue #527「PR #526（Issue #512）のkarte_notify systemMessage直送をmerge後の新規セッションで実機確認する」

- URL: https://github.com/hiratashinnya/review-system/issues/527
- 状態: closed（2026-11-18取得）
- 本文: 2667文字/ 44行。全文: `../raw/issues-2026-09.jsonl`
- AC: 3件（未チェック: 3）
- Issue参照: #512, #526, #270, #513
- PR参照: #526
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- 3. `.claude/hooks/karte-notify.sh`のhook登録は`bash "$CLAUDE_PROJECT_DIR"/.claude/hooks/karte-notify.sh`という形式。`main`ブランチ（本セッションが起動した時点のプロジェクトルート）には`.claude/hooks/karte-notify.sh`が存在しない（PR #526が未mergeのため）。
- なお、Issue #270（closed）は`${CLAUDE_PROJECT_DIR}`の未引用によるfail-open（空白を含むパスでhookが起動しない）を扱っており、本Issueが扱う「セッション開始時点に固定されるか」という論点とは別原因・別現象である（重複ではない）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
