---
id: TD-ISSUE-542-007
version: 1
condition: boundary
---

# 目的

REST 非同期 merge の書き込みと GraphQL merge queue 登録を両 hook の全ロールで拒否し、状態ポーリングと読み取り専用の Git 調査を許可する。Claude native deny は書き込みサブコマンドを拒否し、読み取り系サブコマンドを巻き込まない。

# 前提

- GitHub REST/GraphQL payload は fake command text とし、API call は行わない。
- `agent_command_gate` は Claude/Codex の各 hook 経由で実行する。

# 手順・期待結果

1. `PUT`/`POST .../pulls/{number}/merge-async` を main と全ロールで拒否し、request UUID を指定した `GET .../merge-async/{uuid}` を許可する。
2. `enqueuePullRequest`、`mergePullRequest`、`enablePullRequestAutoMerge` を全ロールで拒否する。`dequeuePullRequest` と `disablePullRequestAutoMerge` は main context で許可する。
3. Claude native permission matcher は `git merge` と引数付き merge を拒否し、`git merge-base`、`git merge-tree`、`git merge-file` を許可する。
4. Claude/Codex の共有 hook は main payload の `git merge-base main topic` を許可する。
