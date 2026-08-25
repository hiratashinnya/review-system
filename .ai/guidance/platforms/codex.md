# Codex 固有 guidance

- Codex 固有の設定・hook・custom agent は `.codex/` 配下に置く。
- Codex repo skill は `.agents/skills/` 配下に置く。
- 実装、commit、push、PR 作成、PR レビュー、修正は、Codex が利用可能な subagent に委譲する。
- shell 経由で GitHub 本文を投稿する場合は body file を優先し、バッククォートや `$()` の shell 展開を防ぐ。
- secondary worktree からの remote 操作後にローカル checkout／cleanup が競合した場合は、remote 状態を確認してから後処理する。

## Codex rate-limit recovery

- project-local Stop hook は rate-limit の兆候がある場合だけ `/status` を送り、cooldown で再帰を抑える。
- cloud／hosted／no-tmux／tmux-unavailable の no-op 経路では、状態ディレクトリ、payload、ログなどの永続副作用を起こさない。
- tmux pane 注入ガードの既定は `^codex$` とし、wrapper が必要な環境だけ明示的に上書きする。
- Codex 資産を `.claude/` に混ぜない。Codex hooks/config/custom agents は `.codex/`、repo skills は `.agents/skills/` に置く。
