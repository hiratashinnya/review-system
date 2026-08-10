# Managed PR merge hook 運用確認

この runbook は Claude/Codex の managed tool path だけを対象にする。GitHub UI、hook 外の API、direct push/ref update、および製品が標準 hook path を適用しない specialized tool は保証範囲外である。GitHub Actions は primary gate に使用しない。

## 有効化と trust

Codex の project hook は、現行の [Codex Hooks仕様](https://learn.chatgpt.com/docs/hooks) に従い、project を信頼し、さらに `/hooks` で現在の hook definition hash を確認・信頼した場合だけ読み込まれる。`[features] hooks = false` が有効な環境では発火しない。hook、classifier、設定の変更後は定義hashが変わるため、必ず再度 `/hooks` で確認する。

Claude でも project hook 設定を有効化し、表示された project hook の信頼確認を完了する。信頼確認をしていない環境を「managed gate 有効」と記録してはならない。

## Actions 非依存の実発火確認

1. GitHub Actionsを参照・起動せず、対象worktreeでClaude/Codexの新規sessionを開始する。
2. hook一覧で、PR merge matcherに対する `PreToolUse` と `PostToolUse` が同じ `pr-merge-gate.sh` を指すことを確認する。
3. 副作用のない probe として managed auto-merge enable toolを呼び出す。`AUTO_MERGE_DENIED` でtool実行前に拒否されなければfailとする。
4. audit JSONLの最新 `pre_use_decision` に、現在の `hook_asset_hash`、`hook_event_id`、`classifier_version` があり、`operation_dispatched=false`、`merge_api_called=false` であることを確認する。
5. 実mergeは通常のレビュー・承認後だけ行う。`ALLOW` のpre recordと同じ `invocation_id` / `operation_fingerprint`を持つ `post_use_completion` が一件あり、`operation_dispatched=true` とredacted `response_fingerprint`が記録されることを確認する。`merge_api_called=true` はconnectorの明示的な `merged=true` responseでAPI到達を証明できた場合だけである。CLI/RESTの終了コード、connector失敗、未知responseでは `null`（`NOT_PROVEN`）が正しく、Postへ到達した事実だけからAPI呼出し済みと解釈しない。

probeの結果、hook failure、audit書込み失敗、Pre/Post相関欠落、未知alias/wrapper、新しいmerge connectorのいずれかを検出した環境はfail-close扱いとし、managed mergeを実行しない。

file-backed GraphQL（`-F query=@file` / `@-` / `--input`）は、hookの検査後にGitHub CLIが再読する内容へpermitを束縛できないためfail-closeである。未知実行名に続く `pr merge` / merge相当APIもfail-closeにし、known-safeな `gh alias list` / `gh extension list` と、`echo`等の明確な非merge形だけをgate対象外にする。

## 証跡判定

有効・発火済みの証跡は、設定ファイルの静的存在だけでは不十分である。環境ごとに次を揃える。

- trust済みのhook definition hashと確認時刻
- `hook_asset_hash`を含むauto-merge deny probeのpre record
- 許可された実mergeについて、head/base/default branch、merge method、closing set、dependency pathを含むpre record
- 同じinvocationに相関したPostToolUse completion record

リポジトリのunit testはClaude/Codex双方の実スクリプトをsubprocessで起動し、ActionsなしでdenyとPre/Post相関を検証する。ただし、製品UI上のtrust状態そのものはsessionごとの外部状態なので、このrunbookの実環境確認を置き換えない。
