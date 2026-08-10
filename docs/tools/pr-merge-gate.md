# Managed PR merge pre-use gate

## 保護対象

`.codex/hooks.json` と `.claude/settings.json` は、Bashおよび登録済みGitHub connectorの
`PreToolUse` から共通の `python3 -m pr_merge_gate.hook` を呼ぶ。分類対象は次である。

- `gh pr merge N --merge|--rebase|--squash` と、`-R/--repo` を持つ同形式
- `rtk` / `rtk proxy` / `command` / `builtin` / `exec` のallowlist wrapper
- `gh api -X PUT repos/OWNER/REPO/pulls/N/merge`（merge method明示必須）
- `github_merge_pull_request` と登録済みMCP canonical tool name
- CLI/GraphQL/connectorのauto-merge enableは常に `BLOCK/AUTO_MERGE_DENIED`

method省略、unknown alias/wrapper/flag/tool、target不明、interception不能なmerge相当操作は
`ERROR` で拒否する。UI merge、hook外API、direct push/ref updateはunmanagedであり、本gateに
保護されているとは表示しない。

## 実行順序

1. tool name/inputをshell evaluateせずclosed classifyし、repository/PR/method/override/headを束縛する。
2. GitHub standard APIをfresh readし、PR/head/base/default、closing relation全cursor、source commit、
   parent/tree、repository settingsを取得する。
3. merge/rebase/squashで実際にdefault branchへ届くmessageだけを再構築し、commit-message-only
   closing keywordをGraphQL relation setへunionする。
4. #296の共通dependency/closure evaluatorへ一括virtual closeを渡す。waiver lifecycleが#299で
   完成するまではwaiverをpermit根拠にしない。
5. `ALLOW`候補だけ同じsnapshotをfresh再読する。変化時は最大3attempt再評価し、安定しなければ
   `ERROR/REEVALUATION_LIMIT`。一致した `ALLOW` だけ元のintercepted operationを一度続行する。
6. `BLOCK/ERROR` はPreToolUse denyを返すため、元merge APIは未呼出しのまま終了する。

## Resultとaudit

resolverのcontrol JSONはPolicy 1.0の`blocker-gate-result/v1`、hook evidenceは
`pr-merge-evidence/1`である。deny理由は日本語のnext actionを含む。redacted decisionは
`${XDG_STATE_HOME}/review-system/blocker-gate/audit.jsonl`、未設定時は
`${HOME}/.local/state/review-system/blocker-gate/audit.jsonl`へ0600でappend+fsyncする。
raw command、token、header、PR本文、commit messageは保存しない。安全なappendができなければ
`ERROR/HOOK_INTEGRITY_ERROR` とし、permitを発行しない。
audit schema `pr-merge-audit/4` は、override fingerprint、message source/delivered fingerprint、
repository merge settings、snapshot、attempt、PR state/draft、blocker Result metadata、formatter/evidence
version/hashをpre/post相関レコードへ保存する。生messageは保存しない。

## 運用確認

両harnessでproject hookをtrust/enabledにし、`/hooks` とdebug logでregistrationとactual fireを
確認する。Actions statusはprimary allow根拠ではなく、GitHub Freeのstandard API以外の有料
serviceは使用しない。
