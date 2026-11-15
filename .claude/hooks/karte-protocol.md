# 是正ループの診断カルテ手順（SubagentStart 注入・Issue #309）

これは `issue-fixer` の起動時に `SubagentStart` フックが自動注入する手順書である
（実体＝`.claude/hooks/subagent-karte-inject.sh`）。本文はシェルから分離されており、
内容を変えたいときはこのファイルだけを編集すればよい（`inject-governance.sh` と同作法）。

**あなた（`issue-fixer`）はこのラウンドで、着手前に診断をカルテへ登録すること。**
`.claude/agents/issue-fixer.md` の「Step 1 の診断（`karte render`→`karte append`）を経ずに
`Edit`/`Write` しない」契約を、この注入が毎回のラウンドで思い出させる
（例外は PR base 取り込みの衝突解消だけ＝`.ai/agents/issue-fixer.md`「取り込みとカルテ手順の順序」）。

## 1. 着手前：過去の試行を読む

**この手順書の直後（`---` の下）に `python3 -m karte render --issue <N>` の出力が既に
添付されている**（K-14：フックが実行して `additionalContext` に載せる。呼び忘れの余地を
無くすため注入側に寄せてある）。まずそれを読むこと。添付が無い場合＝進行ポインタが
読めない等でフックが render を落としたときだけ、自分で実行する:

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

**これを通してから `Edit`/`Write` に入る**（PR base 取り込みの衝突解消だけは例外＝4. の末尾）。拒否されたらアプローチを変える
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

**この拒否は同じ停止要求に対して1回だけ**（2回目は `stop_hook_active` により素通しする）。
判定不能の理由が**あなたには直せないもの**（進行ポインタの再生成＝`ingest-review` は
是正当事者に許されない）でも詰まないようにするための逃げ道であって、
「2回止めれば通る」という運用ではない。1回目の block reason を読み、
できる記録（`append` / `close-attempt`）は必ず済ませてから停止すること。

**例外：PR base の取り込みが原因で、診断登録より前に停止する場合。** 取り込み（`gitgate integrate-base`）は
Step 0 の後・診断より前に行い、その衝突解消の編集は是正の編集ではない（診断登録の対象にしない）。
ただし衝突解消の編集は解消に必要な最小限に留めて finding の是正を混ぜず、finding 自体が
取り込み・衝突解消を求める場合は通常どおり 2. の診断を経る。
取り込みが原因の STOP（`integrate-base-abort` での中止、判断できない衝突、記録と異なる merge の進行中、
`BASE_STATE_INVALID`、policy 1.x の取り込みの残存など）が**このラウンドの最初の `append` より前**なら、
この拒否に応じて `append` も `close-attempt` も**実行しない**——試していないアプローチが Attempt として
残り、再 dispatch 後の是正が類似判定の飽和で拒否されうるうえ、クローズ済みの Attempt が後の
診断前編集を `karte check` に通してしまう。STOP の原因（中止した場合は退避 tar のパスも）を
ハンドオフの `stop_reason` に書き、もう一度停止する。
`append` より後の STOP はこの例外に当たらず、未クローズの Attempt があれば通常どおり実際の結果で
`close-attempt` してから停止する（push 直後に既にクローズ済みなら、そのまま停止できる）。
詳細は `.ai/agents/issue-fixer.md`「取り込みとカルテ手順の順序」。

## `{issue, round}` の出所

**dispatch prompt はフックに届かない**（`SubagentStart` payload に含まれない）。
`<N>` / `<R>` の唯一の情報源は進行ポインタ `tmp/_karte/active.json` であり、
フック（注入・停止ゲートとも）もあなたも同じそこを見る。
`karte` CLI は `--issue` / `--round` を省略すればポインタから補完するが、
**並行運用時に別 Issue の台帳を書かないよう `--issue` は必ず明示する**
（フックが実行する `karte render` も同じ理由で `--issue` を明示している）。

カルテの所在は `karte` CLI が `main_worktree_root()`（`.git`→`commondir`）で決定論的に
解決する——**linked worktree から呼んでも必ずメインワークツリーの台帳に収束する**（K-01）。
パスを自分で組み立てず、`Read`/`Write` でカルテファイルを直接触らないこと。

## 是正当事者がやらないこと

`ingest-review` は**是正当事者には許さない**（自分への指摘を自分で台帳へ書き換えられる）。
`ingest-reviewer`・`decide`・`activate` も許されない。レビュー結果の取り込みは、`pr-reviewer`
本人（`ingest-reviewer`）か主文脈（`ingest-review`）が行う（Issue #308 / #341 / #375）。
実装・是正担当の `out_of_scope_findings` は主文脈が最新 round を明示して取り込む。申告原本がある
Issue は保護モードとなり、オーナー決定を保持し、再掲漏れは未解消のまま引き継ぐ。
