1. `git add -A`：終了コード **128**
2. `git -c user.name=probe -c user.email=probe@example.invalid commit --allow-empty -m probe-commit`：終了コード **128**

標準エラーは両方とも同じです。

```text
fatal: Unable to create '/home/hiras/ws_claude/codex-verify/review-system/.git/worktrees/agent-verify-in/index.lock': Read-only file system
```

ファイル編集・テスト実行はありません。コミットは作成されていません。