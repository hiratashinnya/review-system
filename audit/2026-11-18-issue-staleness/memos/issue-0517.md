# Issue #517「gated ロールが Task で非 gated サブエージェントを spawn し agent-command-gate の allowlist を迂回できる」

- URL: https://github.com/hiratashinnya/review-system/issues/517
- 状態: closed（2026-11-18取得）
- 本文: 4881文字/ 78行。全文: `../raw/issues-2026-09.jsonl`
- AC: 6件（未チェック: 6）
- Issue参照: #516, #510, #515, #129, #452
- PR参照: #516, #515
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ### 実測（2026-09-15・PR #516 の実装中に発生） | ### 経路の詳細 | ### 影響範囲 | ### 既知の限界との関係 | ### 利用可能な機構（2026-09-15 調査・Claude Code 2.1.263） | ## Scope | ### `Task` 剥奪の副作用（意図的に受け入れる） | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- 同じ手口は read-only でないコマンドにも使える。`pr-reviewer` の `git push` 禁止、`issue-fixer` の `karte ingest-review` 禁止、危険コマンド層（`curl`/`ssh`/`python3 -c` 等）——**agent-command-gate.sh が守っている非対称権限のすべてが、同じ方法で骨抜きにできる**。`.claude/rules/05-skills-agents.md` 
- 3. 上記の契約文（`.ai/agents/issue-implementer.md`・`issue-fixer.md` と Claude 固有ファイル）を、`Task` 非保有を前提とする記述へ更新する。
- 現在の frontmatter は `Task` の用途を「**corpus ノード委譲**」と説明している（`doc-system-v2/nodes/**` を `*-author` → `reconciliation-validator` → `reconciliation` の経路で著作するため）。`Task` を外すと、gated ロールは corpus ノードを要する Issue に当たったとき **STOP して主文脈へ報告する**ことになる。
- - [ ] 契約文（`.ai/agents/*` と `.claude/agents/*`）が `Task` 非保有を前提とする記述へ更新され、corpus ノードを要する場合は STOP して主文脈へ報告する手順が明記されていること。
- - 関連: #129（`agent-command-gate.sh` の fail-open / 正規表現回避・closed）——ゲートが sandbox ではないという同じ制約系に属するが、root cause は異なる（#129 は Bash 文字列検査の不備、本件は `Task` 委譲経路の未検査）。
- - 関連: #452（Codex issue-pipeline の implementer/fixer を隔離 worktree へ機械束縛する・open）——別ハーネス（Codex）の別機構だが、gated ロールの実行境界を機械で強制するという目的を共有する。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
