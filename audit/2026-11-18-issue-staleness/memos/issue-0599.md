# Issue #599「Codex hook まわりの文書・コメントの不整合（Stop hook 言及・hook 一覧の漏れ）」

- URL: https://github.com/hiratashinnya/review-system/issues/599
- 状態: closed（2026-11-18取得）
- 本文: 1264文字/ 31行。全文: `../raw/issues-2026-10.jsonl`
- AC: 3件（未チェック: 3）
- Issue参照: #596, #569
- PR参照: #596
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- PR #596 で Codex の Stop hook を撤去した後も、Codex hook まわりの文書・コメントに現状と合わない記述が2点残っている。動作には影響しないが、読み手に誤解を与える。PR #596 のスコープ外のため、別 Issue で扱う。
- 1. `.codex/hooks/agent-command-gate.sh:197` のコメントに「Worktree release verbs remain limited to the main context and stop hook.」とある。`.codex/hooks.json` に登録されているフックは `PreToolUse` のみで、Codex の Stop hook は撤去された。このコメントの `stop hook` が何を指すか（
- - 上記1のコメントを現状に合わせる（指す対象を確認し、必要なら修正または削除）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
