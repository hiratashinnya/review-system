# Codex project guidance

- すべての説明・報告・質問は日本語で行う。ユーザーが明示的に別言語を指定した場合を除き、main thread・subagent・レビュー報告・PR コメントのいずれも日本語で統一する。
- Codex 固有の設定・hook・custom agent は `.codex/` 配下に置く。
- Codex repo skill は `.agents/skills/` 配下に置く。

## 継続指示

- PR 本文、PR コメント、レビューコメント、merge コメントを Codex が投稿する場合は、ユーザーが明示的に別指示した場合を除き、本文冒頭または件名で **Codex AI agent** 由来であることを明記する。
- `/new` や `/clear` 後にも効くプロジェクト運用指示として、main thread は作業分解、Bloom 分類、sub-agent 委譲、進行管理、ユーザー報告に限定する。
- 実装、commit、push、PR 作成、PR レビュー、修正は sub-agent に委譲する。完了報告は commit、push、PR 作成、別文脈レビューが完了してから行う。
- ユーザーが「別コンテキスト」「subagent」「レビューと修正を分離」と指示した場合、レビュー担当 subagent と修正担当 subagent/主文脈を分ける。修正後は、元レビューとは別の文脈で再レビューしてから完了判断する。
- PR レビューで所見が出た場合は、所見を PR コメントとして残してから、レビュー担当と修正担当を分けて修正する。修正後は別文脈で再レビューし、対応内容・検証・最終レビュー結果を PR コメントに残す。
- `gh pr comment --body` など shell 経由で本文を投稿する時は、バッククォートや `$()` が shell 展開されない引用方法を使う。長い本文は body file を優先する。
- secondary worktree から `gh pr merge` すると、remote merge は成功してもローカル checkout/cleanup が main worktree 競合で失敗することがある。失敗時は `gh pr view` で `state: MERGED` を確認し、必要なら remote branch を明示削除する。

## 今回の教訓

- Codex rate-limit recovery は project-local `Stop` hook で `/status` を送って reset 時刻を読む。通常 Stop では rate-limit 兆候がある場合だけ `/status` を送り、cooldown で `/status` 自身の Stop 再帰を抑える。
- cloud/hosted/no-tmux/tmux-unavailable の no-op 経路では、`STATE_DIR` 作成、payload 保存、ログ書き込みを含む永続副作用を起こさない。
- tmux pane への注入ガードは安全側を既定にする。`CODEX_RL_PANE_CMD_RE` の既定は `^codex$` とし、`node` wrapper が必要な環境だけ明示的に env で上書きする。
- Codex 用資産を `.claude/` に混ぜない。Codex hooks/config/custom agents は `.codex/`、Codex repo skills は `.agents/skills/` に置く。
