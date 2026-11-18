# Issue #350「issue-implementer の「isolated worktree」記述が実装と食い違う：gitgate new-branch は worktree を作らず呼び出し元の working tree を branch switch する」

- URL: https://github.com/hiratashinnya/review-system/issues/350
- 状態: closed（2026-11-18取得）
- 本文: 2188文字/ 40行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 3件（未チェック: 3）
- Issue参照: #344, #323
- PR参照: なし
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## 影響 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- `.claude/agents/issue-implementer.md` の description は「Implements a GitHub Issue end-to-end in an **isolated worktree**」と明記し、本文中にも `.worktrees/<name>/` を cwd にするケースを前提とした記述（handoff_path が worktree 配下の相対パスへ解決される問題への対処）がある。しかし、このロールの
- - `gitgate/cli.py` の `verb_new_branch`（129-136行）は `["git", "switch", "-c", request.branch_name, request.base_oid]` を返すだけで、これは**現在の working tree 上でブランチを切り替える**操作。`git worktree add` 相当は呼ばれない。
- - `.claude/agents/issue-implementer.md` 本文が言及する「linked worktree（`.worktrees/<name>/`）を cwd にすると相対 `tmp/_handoff/` がその worktree 配下に解決される」という懸念は、実際には発生し得ない（worktree 自体が作られないため）——ドキュメントが実在しない実行経路を前提に書かれている。
- - Blocked by: なし

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
