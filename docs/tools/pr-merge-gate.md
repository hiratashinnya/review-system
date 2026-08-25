# Managed PR merge pre-use gate

## 保護対象

`.codex/hooks.json` と `.claude/settings.json` は、Bashおよび登録済みGitHub connectorの
`PreToolUse` から共通の `python3 -m pr_merge_gate.hook` を呼ぶ。分類対象は次である。

- `gh pr merge N --merge|--rebase|--squash` と、`-R/--repo` を持つ同形式
- `rtk` / `rtk proxy` / `command` / `builtin` / `exec` のallowlist wrapper
- `gh api -X PUT repos/OWNER/REPO/pulls/N/merge`（merge method明示必須）
- `github_merge_pull_request` と登録済みMCP canonical tool name
- Codex hosted GitHub Apps の `codex_apps.github.merge_pull_request` と `codex_apps.github.enable_auto_merge` は hook 外なので `.codex/config.toml` で app id `connector_76869538009648d5b282a4bb21c3d157` の該当 tool だけ無効化
- CLI/GraphQL/hookable connectorのauto-merge enableは常に `BLOCK/AUTO_MERGE_DENIED`

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
audit schema `pr-merge-audit/4` は、GraphQL expected commit count、override fingerprint、message source/delivered fingerprint、
repository merge settings、snapshot、attempt、PR state/draft、blocker Result metadata、formatter/evidence
version/hashをpre/post相関レコードへ保存する。生messageは保存しない。

### pre/post相関のidentity（Issue #414）

pre-use decisionとpost-use completionは `invocation_id` で相関する。
`invocation_id = uuid5(NAMESPACE_URL, "<session_id>\0<tool_use_id>")` であり、
**`turn_id` は鍵に含めない**。`tool_use_id` はsession内で1回のtool呼び出しに一意なので
`turn_id` は識別力を足さない一方、harnessによって `PreToolUse` と `PostToolUse` で
送出有無が揃わない任意フィールドである（実測：Claude Code は `PreToolUse` で `turn_id` を
送らない）。鍵に混ぜると同一tool呼び出しがpreとpostで別IDになり、
`append_completion` がpermitを見つけられず post-use completion が永久に記録されない。

permit走査はJSONとして読めない行を読み飛ばす。append-onlyの共有ログには別プロセスの
interleaved writeで壊れた行が混じり得るが、1行の破損でpost-use auditが恒久停止するのは
監査証跡の可用性を落とすだけで安全性を上げない（読み飛ばしはpermitを「見つけられない」
方向にしか働かず、permitなしでcompletionを発行する経路は増えない＝fail-closeは維持）。

### PostToolUse失敗のreason code（Issue #414）

`PostToolUse` の失敗は `POST_AUDIT_INTEGRITY_ERROR/<code>` で報告する。`<code>` は
redaction安全な固定語彙で、payload由来の文字列（command・PR本文・token）を含まない。

| code | 意味 |
|---|---|
| `PAYLOAD_INVALID` | payloadがJSONでない／`hook_event_name`・`session_id`・`tool_use_id`・`tool_name`・`tool_response` が契約を満たさない |
| `RECLASSIFIED_NOT_MERGE` | PostToolUseでの再分類がmergeにならない（PreToolUseでdenyされたはずの操作が到達した） |
| `PERMIT_MISSING` | この `invocation_id` を持つpermit済みpre-useレコードが1件も見つからない（auditファイル不在／pre-use hookが動かなかった／当該行が破損して読み飛ばされた、のいずれか） |
| `PERMIT_OPERATION_MISMATCH` | `invocation_id` のpermitは在るが `operation_fingerprint` が食い違う＝許可した操作と実行された操作が別物（Issue #436）。実測された発生源は、同一PreToolUseイベントに登録された別hookが `hookSpecificOutput.updatedInput` で `tool_input.command` を書き換え（例: `gh pr merge …` → `rtk gh pr merge …`）、本gateが分類した文字列と実際に実行された文字列がずれるケース |
| `HOOK_ASSET_UNREADABLE` | hook asset一式のhash計算に失敗した |
| `AUDIT_FILE_UNSAFE` | audit fileがsymlink／別uid所有／0600以外 |
| `AUDIT_PATH_INVALID` | `HOME`/`XDG_STATE_HOME` が無い、または絶対pathでない |
| `AUDIT_READ_FAILED` / `AUDIT_WRITE_FAILED` | audit fileの読み書きがOSレベルで失敗した |

`PERMIT_MISSING` と `PERMIT_OPERATION_MISMATCH` はいずれもfail-close（completionを追記せず
PostToolUseをblockする）である点は同じだが、原因（相関鍵の欠落／整合性違反）は別物であり、
Issue #436はこれを分けた（Issue #414が例外クラス名だけの報告を割った理由がそのまま一段下にも
当てはまる）。

以前は例外クラス名（`AuditError`）だけを出していたため、構造的に別物の複数経路が同じ
文字列で報告され、報告を受けても再現なしには原因を特定できなかった。

## 運用確認

両harnessでproject hookをtrust/enabledにし、`/hooks` とdebug logでregistrationとactual fireを
確認する。Actions statusはprimary allow根拠ではなく、GitHub Freeのstandard API以外の有料
serviceは使用しない。
