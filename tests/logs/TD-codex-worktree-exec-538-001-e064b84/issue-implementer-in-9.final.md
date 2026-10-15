1) 環境変数の確認：終了コード `0`

```text
CODEX_WORKTREE_EXEC_ACTIVE=1
CODEX_SANDBOX_NETWORK_DISABLED=1
```

2) `python3 -m codex_worktree_exec ...`：実行前に拒否されたため、終了コードはありません。

```text
Codex runs as the executor of codex_worktree_exec and must not launch it recursively.
```

実行制御により、`codex_worktree_exec` の実行者からの再帰起動が拒否されました。ファイル変更・テスト実行はありません。