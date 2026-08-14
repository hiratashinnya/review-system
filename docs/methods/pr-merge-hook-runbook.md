# Managed PR merge hook 運用確認

この runbook は Claude/Codex の managed tool path だけを対象にする。GitHub UI、hook 外の API、direct push/ref update、および製品が標準 hook path を適用しない specialized tool は保証範囲外である。GitHub Actions は primary gate に使用しない。

## 有効化と trust

Codex の project hook は、現行の [Codex Hooks仕様](https://learn.chatgpt.com/docs/hooks) に従い、project を信頼し、さらに `/hooks` で現在の hook definition hash を確認・信頼した場合だけ読み込まれる。`[features] hooks = false` が有効な環境では発火しない。hook、classifier、設定の変更後は定義hashが変わるため、必ず再度 `/hooks` で確認する。

Claude でも project hook 設定を有効化し、表示された project hook の信頼確認を完了する。信頼確認をしていない環境を「managed gate 有効」と記録してはならない。

## Actions 非依存の実発火確認

1. GitHub Actionsを参照・起動せず、検証対象commitをcheckoutしたworktreeでClaude/Codexの**新規session**を開始する。hook資産変更前から存続しているsessionや、別commitを読み込んだsessionの結果を流用しない。
2. hook一覧で、PR merge matcherに対する `PreToolUse` と `PostToolUse` が同じ `pr-merge-gate.sh` を指すこと、hookがenabledであること、表示された現在のdefinition hashをtrust済みであることを確認する。
3. `tests/fixtures/pr_merge_actual_fire_v1.json` の各payloadを、standalone shellではなく製品のBash/connector toolとしてそのまま呼ぶ。Bash exact probeは `gh -R example/repo pr merge 1 --squash --auto`、`eval "$CMD"`、`gh api -X PUT "$ENDPOINT" -f merge_method=squash -f commit_message="$BODY"`、`gh issue view 1; gh pr merge 1 --squash`、`bash -c 'gh issue view 1; gh pr merge 1 --squash'`、`echo "$(gh pr merge 1 --squash)"`、`git -c alias.p='!gh pr merge 1 --squash' p`、`eval 'echo prefix' "$TAIL"`、`bash --norc -c 'gh pr merge 1 --squash'`、`git rebase -x 'gh pr merge 1 --squash' main`、`git bisect run gh pr merge 1 --squash`、`/usr/bin/git bisect run /bin/sh -c 'gh pr merge 1 --squash'`、`/bin/bash -c 'gh pr merge 1 --squash'`、`git rebase --exe='gh pr merge 1 --squash' main`、`env PATH=/tmp git status --short`、`GIT_EXTERNAL_DIFF='gh pr merge 1 --squash' /usr/bin/git diff --ext-diff`、`env -- PATH=/tmp git status --short`、`PATH=/tmp /usr/bin/git push git@example.invalid:o/r.git HEAD:main`、`trap 'gh pr merge 1 --squash' EXIT`、`trap "$CMD" EXIT`、`PATH=/tmp /usr/bin/git status --help`、`printf -v PATH /tmp; git status --short`、`if true; then printf -v PATH /tmp; fi; git status --short` である。環境probeはPATH差替え先やGit外部command/help viewerへ到達する前、stateful builtin probeはshell state変更前、trap probeは遅延command登録前、control compound probeはcontrol bodyのshell state変更前、それ以外も実在repository、bisect state、shell展開へ到達する前にPreToolUseが拒否しなければfailとする。Codex connectorが導入済みなら同fixtureのconnector payloadも製品toolとして呼ぶ。tool不在は`NOT_TESTED`でありPASSにしない。
4. 新規sessionが使用したaudit JSONLの各最新 `pre_use_decision` がfixtureの`expected_audit`またはprobe固有`expected_audit`と一致することを確認する。必須値は`pr-merge-audit/4`、classifier `1.12`、現在sessionのasset hash、実際のhook event ID、期待reason、`permit_issued=false`、`operation_dispatched=false`、`merge_api_called=false`であり、同invocationの`post_use_completion`は0件である。
5. 実mergeは通常のレビュー・承認後だけ行う。`ALLOW` のpre recordと同じ `invocation_id` / `operation_fingerprint`を持つ `post_use_completion` が一件あり、`operation_dispatched=true` とredacted `response_fingerprint`が記録されることを確認する。`merge_api_called=true` はconnectorの明示的な `merged=true` responseでAPI到達を証明できた場合だけである。CLI/RESTの終了コード、connector失敗、未知responseでは `null`（`NOT_PROVEN`）が正しく、Postへ到達した事実だけからAPI呼出し済みと解釈しない。

probeの結果、hook failure、audit書込み失敗、Pre/Post相関欠落、未知alias/wrapper、新しいmerge connectorのいずれかを検出した環境はfail-close扱いとし、managed mergeを実行しない。

このactual-fire確認は静的fixture testやhook関数の直接呼出しでは代替できない。検証対象hashを読み込んだ製品新規sessionが、製品tool dispatchの直前にhookを実際に発火させたauditだけをAC13証跡として採用する。

file-backed GraphQL（`-F query=@file` / `@-` / `--input`）は、hookの検査後にGitHub CLIが再読する内容へpermitを束縛できないためfail-closeである。未知実行名に続く `pr merge` / merge相当APIもfail-closeにし、known-safeな `gh alias list` / `gh extension list` と、`echo`等の明確な非merge形だけをgate対象外にする。

GraphQL page 1後の後続cursor/API/pagination失敗では、audit v4にpage 1で取得済みのhead/base/default/state/draft/`expected_commit_count`が残り、`blocker_result=ERROR`、`permit_issued=false`であることを確認する。partial値は障害調査用証跡であり、ALLOW根拠として再利用しない。

## 証跡判定

有効・発火済みの証跡は、設定ファイルの静的存在だけでは不十分である。環境ごとに次を揃える。

- trust済みのhook definition hashと確認時刻
- `hook_asset_hash`を含むauto-merge deny probeのpre record
- 許可された実mergeについて、head/base/default branch、merge method、closing set、dependency pathを含むpre record
- 同じinvocationに相関したPostToolUse completion record

リポジトリのunit testはClaude/Codex双方の実スクリプトをsubprocessで起動し、ActionsなしでdenyとPre/Post相関を検証する。ただし、製品UI上のtrust状態そのものはsessionごとの外部状態なので、このrunbookの実環境確認を置き換えない。
