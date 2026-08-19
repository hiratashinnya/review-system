# 是正ループの診断カルテ手順（SubagentStart 注入・Issue #309）

これは `issue-fixer` の起動時に `SubagentStart` フックが自動注入する手順書である
（実体＝`.claude/hooks/subagent-karte-inject.sh`）。本文はシェルから分離されており、
内容を変えたいときはこのファイルだけを編集すればよい（`inject-governance.sh` と同作法）。

**あなた（`issue-fixer`）はこのラウンドで、着手前に診断をカルテへ登録すること。**
`.claude/agents/issue-fixer.md` の「Step 1 の診断（`karte render`→`karte append`）を経ずに
`Edit`/`Write` しない」契約を、この注入が毎回のラウンドで思い出させる。

## 1. 着手前：過去の試行を読む

```
python3 -m karte render --issue <N>
```

`## Prior attempts（DO NOT repeat these）` に挙がっている診断・変更箇所を**なぞらない**。
`## 飽和したアプローチ` に挙がったものと同種の `append` は `EXIT_SATURATED` で拒否される。

## 2. 着手前：今回の診断を宣言する

```
python3 -m karte append --issue <N> --round <R> \
  --finding-ids <F-...> --root-cause <slug> --change-kind <kind> \
  --targets <file::symbol...> --diagnosis "<1行>"
```

**これを通してから `Edit`/`Write` に入る。** 拒否されたらアプローチを変える
（同じ診断で押し切らない）。

## 3. 修正後：実測差分を記録する

```
python3 -m karte close-attempt --issue <N> --outcome <fixed|partial|no-change|regressed>
```

commit・push 後は作業ツリーが `HEAD` と一致して diff が空になる。その場合は
`--base <変更前の commit>` を明示するか `--diff-file` を使う。

## 4. 停止できる条件

```
python3 -m karte check --issue <N> --round <R>
```

これが exit 0 にならない限り、`SubagentStop` フックがあなたの停止を
`{"decision":"block"}` で拒否する（`.claude/hooks/subagent-stop-gate.sh`）。
判定不能（進行ポインタ欠如・破損）も拒否側に倒れる＝fail-close。

## `{issue, round}` の出所

**このフックはデータを押し込まない**（`SubagentStart` payload に dispatch prompt が無い）。
`<N>` / `<R>` は進行ポインタ `tmp/_karte/active.json` が持っている値であり、
`karte` CLI は `--issue` / `--round` を省略すればそこから補完する。
ただし**並行運用時に別 Issue の台帳を書かないよう `--issue` は必ず明示する**。

カルテの所在は `karte` CLI が `main_worktree_root()`（`.git`→`commondir`）で決定論的に
解決する——**linked worktree から呼んでも必ずメインワークツリーの台帳に収束する**（K-01）。
パスを自分で組み立てず、`Read`/`Write` でカルテファイルを直接触らないこと。

## 是正当事者がやらないこと

`ingest-review` は**是正当事者には許さない**（自分への指摘を自分で台帳へ書き換えられる）。
レビュー結果の取り込みは主文脈が実行する（Issue #308 / #341）。
