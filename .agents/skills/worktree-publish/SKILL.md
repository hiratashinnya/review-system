---
name: worktree-publish
description: 認可済みの実装 subagent が、commit とテストを完了した独立 worktree から push、remote commit 一致確認、draft PR 作成までを安全に行う明示的な公開ゲート。実装済みブランチを GitHub へ初めて公開するとき、または追加 commit を既存 remote branch へ公開して draft PR を作るときに使う。main thread、未認可 agent、branch 作成、stage、commit、レビュー、merge には使わない。
---

# Worktree Publish

commit・テスト済みの worktree を、認可済み実装 subagent から draft PR まで公開する。以下を順番どおり実行し、判定不能なら公開せず停止する。

## 境界

- 明示的に認可された実装 subagent だけで使う。main thread では実行しない。
- `agents/openai.yaml` は公式 Codex skill interface manifest 契約である。issue-implementer からの明示参照専用にするため、`policy.allow_implicit_invocation: false` を設定する。
- branch 作成、stage、commit、テスト実行、レビュー、merge を行わない。commit と必要なテストの成功が確認済みであることを入力条件にする。
- `yeet` を汎用公開フローとして置き換えない。`issue-pipeline` の Issue 選択・委譲・レビュー・merge 管理も置き換えない。
- 対象 worktree を各 network command の実行時 cwd にする。network command に `git -C` を使わない。
- agent のコマンド allowlist、sandbox、承認境界を守る。診断目的でも制約を迂回しない。

## 1. 公開前ゲートを確認する

1. 対象 worktree の絶対パス、想定 branch、想定 repository、PR の base branch、PR title/body を確定する。remote は固定の `origin` とし、任意 remote/ref を指定しない。
2. commit 済みであり、必要なテストが全て成功している証跡を確認する。未 commit 変更や未実行・失敗テストがあれば停止する。
3. current branch を確認し、detached HEAD、`main`、想定外 branch なら停止する。issue-implementer では `python3 -m gitgate branch-current` を使う。
4. status で worktree の清潔性と upstream を確認する。issue-implementer では `python3 -m gitgate status` を使う。既存 upstream は原則 `origin/<current-branch>` と一致させる。初回 push 前は upstream 未設定、または worktree 作成時に設定された base branch upstream を暫定的に許容するが、同名 remote branch が未作成であることを読み取り専用確認し、push 後に必ず同名 upstream へ置き換える。それ以外の不一致は停止する。
5. issue-implementer では引数なしの `python3 -m gitgate publish-info` を使う。限定 JSON の `origin_fetch_url` と `origin_push_urls` の**全件**が想定 repository、`current_branch` が想定 branch、`remote_ref` が `refs/heads/<current-branch>`、`local_commit` が現在の local HEAD SHA であることを push 前に必ず確認する。push URL は `remote.origin.pushurl` の全 effective URLで、未設定時は fetch URL に fallback する。URL が1件でも想定外、空、判定不能なら停止する。
6. `remote_exists: false` と `remote_commit: null` を許容するのは、その branch の**初回 push 前だけ**とする。初回 push だと確認できなければ停止する。追加公開では push 前から `remote_exists: true` と `remote_commit` を必須にする。remote/ref 引数を追加したり、更新操作を行う別コマンドへ置き換えない。判定不能なら対象 worktree・branch・想定 repository と不足情報を報告して停止する。

## 2. network・DNS・認証を切り分ける

1. 対象 repository に対する、ロール規則で許可された読み取り専用 GitHub 疎通確認を sandbox 内で実行する。Issue 実装では対象 Issue への `gh issue view <number>` を優先する。
2. `Could not resolve host`、名前解決失敗、または同等の DNS エラーは認証エラーと推測しない。同一の読み取り専用疎通確認を、外部 network 許可を要求してそのまま再試行する。別コマンドへ置き換えると比較不能になるため避ける。
3. 外部許可で成功した場合は sandbox 内 network/DNS 制約と分類する。外部許可でも同じ DNS エラーなら network/DNS 障害として停止する。
4. GitHub への到達性を確認してから認証を診断する。到達性確認前の `gh auth status` の失敗だけで token invalid と判断しない。到達後、ロール規則で許可される場合に限り `gh auth status` を使う。許可されない場合は、読み取り専用疎通確認の認証応答を根拠に分類し、規則を迂回しない。
5. HTTP 401、明示的な bad credentials、到達確認後の認証失敗だけを認証障害として扱う。権限不足は token invalid と分けて報告する。

## 3. push して remote commit を確認する

1. current branch と status を直前に再確認する。
2. 対象 worktree を cwd にして push する。issue-implementer では引数を追加せず `python3 -m gitgate push` を使い、`origin` の同名 branch に upstream を設定する。
3. network/DNS エラーなら「2. network・DNS・認証を切り分ける」と同じ分類を行い、必要な外部 network 許可を要求して同じ push を再試行する。認証と推測しない。
4. push 後に remote refs を更新し、status と remote commit を再確認する。issue-implementer では `python3 -m gitgate fetch`、`python3 -m gitgate status`、`python3 -m gitgate publish-info` の順に使う。
5. upstream が `origin/<current-branch>` で local と upstream が up to date、かつ `publish-info` が同名 `remote_ref` の `remote_exists: true`、非 null の `remote_commit`、`local_commit` を返し、`remote_commit` と `local_commit` が完全一致することを確認する。初回 push 後も remote SHA 不在は許容しない。SHA 不一致、ahead/behind、別 upstream、remote ref 不在、fetch・取得失敗があれば PR を作らず停止する。

## 4. draft PR を作成する

1. PR body に Codex CLI (AI) attribution、変更ファイルごとの具体的な変更理由、検証結果を含める。Issue 全スコープを満たす場合だけ `Closes #<issue>` を含める。
2. 対象 worktree を cwd にし、許可された `gh pr create --draft --base <base> --head <current-branch> --title "..." --body-file <file>` で draft PR を作成する。
3. 作成結果から PR URL を記録する。失敗時は同一内容の PR を重複作成せず、エラー分類と再試行可否を報告して停止する。
4. PR URL、current branch、upstream、remote commit 一致確認、変更ファイル、テスト結果、公開時の障害分類を報告して終了する。レビューや merge へ進まない。
