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
`pr-merge-evidence/1`である。deny理由は日本語のnext actionを含む（reason codeごとの群分けは
下記「PreToolUse denyメッセージのreason code群分け」）。redacted decisionは
`${XDG_STATE_HOME}/review-system/blocker-gate/audit.jsonl`、未設定時は
`${HOME}/.local/state/review-system/blocker-gate/audit.jsonl`へ0600でappend+fsyncする。
raw command、token、header、PR本文、commit messageは保存しない。安全なappendができなければ
`ERROR/HOOK_INTEGRITY_ERROR` とし、permitを発行しない。
audit schema `pr-merge-audit/5` は、GraphQL expected commit count、override fingerprint、message source/delivered fingerprint、
repository merge settings、snapshot、attempt、PR state/draft、blocker Result metadata、formatter/evidence
version/hashをpre/post相関レコードへ保存する。生messageは保存しない。
`/4` からの差分は `post_use_completion` の3フィールド追加だけで、pre側のフィールドは変わらない
（Issue #435 の項目1と項目3を1回のバンプへ集約した）。

| フィールド | 意味 |
|---|---|
| `skipped_unparsable_lines` | permit走査で読み飛ばした壊れた行数（項目1） |
| `permit_operation_fingerprint` | permit側の `operation_fingerprint`（dispatch側は従来どおり `operation_fingerprint`） |
| `operation_fingerprint_matches_permit` | 上記2つが一致したか。透過ラッパーの書き換えでは `false` になり得る（項目3） |

### pre/post相関のidentity（Issue #414・#435）

pre-use decisionとpost-use completionは `invocation_id` と **PR identity（`repository` と
`pr_number`）**で相関する。
`invocation_id = uuid5(NAMESPACE_URL, "<session_id>\0<tool_use_id>")` であり、
**`turn_id` は鍵に含めない**。`tool_use_id` はsession内で1回のtool呼び出しに一意なので
`turn_id` は識別力を足さない一方、harnessによって `PreToolUse` と `PostToolUse` で
送出有無が揃わない任意フィールドである（実測：Claude Code は `PreToolUse` で `turn_id` を
送らない）。鍵に混ぜると同一tool呼び出しがpreとpostで別IDになり、
`append_completion` がpermitを見つけられず post-use completion が永久に記録されない。

**PR identityでの照合はIssue #435 項目3の緩和**である。以前は `operation_fingerprint`
（コマンド全文由来のhash）を照合していたが過敏で、直近のマージ14件中13件を誤って
fail-closeさせていた。原因は、同じPreToolUseイベントに登録された別hook（実測ではrtk）が
`hookSpecificOutput.updatedInput` で `tool_input.command` を `gh pr merge …` →
`rtk gh pr merge …` へ書き換え、`transport` が `cli-direct`→`cli-wrapped` に変わって
fingerprintが一致しなくなること。rtkの書き換え自体はオーナー判断で不可侵なので、照合側を
PR identityへ緩めた。**代償（オーナー承認済み）は、同一PRに対するmerge method・flagの改竄を
検知しなくなること**。dispatch時の値は `operation_fingerprint` と
`permit_operation_fingerprint` の両方をレコードに残すので事後追跡はできる。
**別のPRへの差し替えは引き続き `PERMIT_OPERATION_MISMATCH` で fail-close する。**

permit走査はJSONとして読めない行を読み飛ばす。append-onlyの共有ログには別プロセスの
interleaved writeで壊れた行が混じり得るが、1行の破損でpost-use auditが恒久停止するのは
監査証跡の可用性を落とすだけで安全性を上げない（読み飛ばしはpermitを「見つけられない」
方向にしか働かず、permitなしでcompletionを発行する経路は増えない＝fail-closeは維持）。
**読み飛ばしは無音にしない**（Issue #435 項目1）——成功時は `post_use_completion` の
`skipped_unparsable_lines` に、completionを書けなかった失敗時は
`AUDIT_UNPARSABLE_LINES_SKIPPED count=<n>` としてstderrに出す。件数はpayload由来の
文字列を含まないのでredactionを壊さない。

### auditの件数ローテーション（Issue #435 項目2）

audit.jsonlは **300件を超えたら直近100件だけ残す**（`pr_merge_gate/audit.py::rotate_records`）。
時間基準は採らない——`pre_use_decision` の大半が自身のtimestampを持たず、現行スキーマでは
保持期間を機械判定できない（Issue #436 の実測：331件/574KB・約110件/日）。

起動点は **PostToolUse hookのみ**で、`post_run` の**分類より前**に置く。分類の後ろに置くと
「mergeと再分類できた場合」の分岐にしか入らず、マージ成立時（実測3日で14件）しか起動しない。
増加要因の大半はdenyレコード（同期間で約330件）なのでそれでは抑えられない。PreToolUse
（`run`）側からは起動しない——permit発行前にread-modify-writeを挟むと、これから相関する
自分自身のpermitを消し得る。

レース安全は次の3点で構造的に担保する。

1. 起動点が分類前なので、この呼び出し自身が書く `post_use_completion` はまだ存在しない。
2. 対応する `pre_use_decision` permitは直近100件にほぼ必ず入るが「ほぼ」では誤
   `PERMIT_MISSING` を生むため、当該 `invocation_id` の行は位置に関係なく必ず残す。
3. 読み書きは `flock` 排他下で **同一inodeをin-placeに切り詰める**。`os.replace` による
   inode差し替えだと、ロック解放を待っていた別プロセスのappendが孤立inodeへ書き込み、
   レコードが黙って失われる。appendも同じロックを取るので追記と切り詰めは直列化される。

ローテーションの失敗はblockではなく `AUDIT_ROTATION_SKIPPED/<code>` としてstderrへ出すだけに
する。ローテーションはpermit経路ではなく衛生処理であり、ここでblockすると merge と無関係な
Bashコマンドまで一律で止まる。auditが実際に危険な状態なら、その後の `append_completion` が
従来どおりfail-closeする。

### PreToolUse denyメッセージのreason code群分け（Issue #457）

`pr_merge_gate/hook.py::_reason()` が返すPreToolUse deny理由（`permissionDecisionReason`）は、
`docs/methods/blocker-gate-pre-use-policy.md` §10.2のreason codeを次の3群に分け、群ごとに
異なる断定表現・next actionを出す。以前は`evidence['reason']`の値によらず常に単一の定型文
「元のmerge操作は送信しません。blocker/API/hook状態を解消後に再実行してください。」を返して
おり、特に分類不能群（マージ操作ではない可能性が高い）でもマージ操作だったと決めつける
誤解を招く文言になっていた。

| 群 | 対象reason | メッセージの趣旨 |
|---|---|---|
| BLOCK群 | `OPEN_BLOCKER`、`CLOSURE_OPEN_DESCENDANT`、`TARGET_ISSUE_NOT_OPEN`、`PR_NOT_OPEN`、`PR_DRAFT`、`AUTO_MERGE_DENIED` | マージ操作と分類され、ポリシー上ブロックされた。「元のmerge操作は送信しません」は事実として述べ、reason別の状況説明を添える |
| 分類不能群 | `CLASSIFIER_UNKNOWN`、`TARGET_AMBIGUOUS`、`MODE_MISMATCH` | マージ操作かどうか自体を確認できず、念のため見送った（マージ操作ではない可能性が高い）。「元のmerge操作は送信しません」のような断定表現は使わず、マージ操作でない場合の代替手段（コマンドの単純化・`python3 -m gitgate` 経由）を案内する |
| 外部要因・内部エラー群 | 上記2群以外のERROR reason（`API_UNAVAILABLE`・`API_PERMISSION`・`GRAPH_CYCLE`・`WAIVER_INVALID`・`HOOK_INTEGRITY_ERROR`等） | マージ操作と分類はできたが、安全確認自体が完了できなかった。reason別の失敗理由を添えて再実行を案内する |
| （3群のいずれにも属さない未知reason） | policy改訂で新規追加されたが実装の3群へ未反映のcode等 | マージ操作かどうかを断定できないため、BLOCK群・外部要因群のような「マージ操作と判定されました」という表現は使わない。実装側のreason code分類を見直すよう案内する |

reason別の一言説明は `pr_merge_gate/hook.py::_REASON_DETAILS` を正本とする（本表は群の対応
関係だけを示す）。3群は `_BLOCK_REASONS`・`_UNCLASSIFIED_REASONS`・
`_EXTERNAL_INTERNAL_ERROR_REASONS` の3つのfrozensetとして明示的に定義されており（暗黙のelse
による分類はしない）、`docs/methods/blocker-gate-pre-use-policy.md` §10.2のBLOCK/ERROR全codeが
この3群のいずれかにちょうど1回現れることを
`tests/unit/test_pr_merge_hook.py::test_all_policy_reason_codes_are_classified_into_exactly_one_group`
がpolicy本文と突合してfail-closeに検知する（Issue #457 F-457-01。policy改訂への追従漏れで、
反映されていない新規codeが黙って外部要因・内部エラー群へ落ち「マージ操作と判定されました」と
誤断定するのを防ぐ）。

### PostToolUse失敗のreason code（Issue #414）

`PostToolUse` の失敗は `POST_AUDIT_INTEGRITY_ERROR/<code>` で報告する。`<code>` は
redaction安全な固定語彙で、payload由来の文字列（command・PR本文・token）を含まない。
Issue #457以降、実際に出力されるメッセージ（stdoutのblock decisionとstderrの両方）は
`<code>` に続けて下表の意味を要約した説明も含む（正本は
`pr_merge_gate/hook.py::_POST_AUDIT_REASON_DETAILS`）。以前は`<code>`だけを出しており、
意味を確認するには本ドキュメントを別途参照する必要があった。

| code | 意味 |
|---|---|
| `PAYLOAD_INVALID` | payloadがJSONでない／`hook_event_name`・`session_id`・`tool_use_id`・`tool_name`・`tool_response` が契約を満たさない |
| `RECLASSIFIED_NOT_MERGE` | PostToolUseでの再分類がmergeにならない（PreToolUseでdenyされたはずの操作が到達した） |
| `PERMIT_MISSING` | この `invocation_id` を持つpermit済みpre-useレコードが1件も見つからない（auditファイル不在／pre-use hookが動かなかった／当該行が破損して読み飛ばされた、のいずれか） |
| `PERMIT_OPERATION_MISMATCH` | `invocation_id` のpermitは在るが PR identity（`repository` / `pr_number`）が食い違う＝**許可したPRと実行されたPRが別物**（Issue #436で分離・#435で照合単位をPRへ変更）。透過ラッパーによるコマンド文字列の書き換えではもう発生しない |
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

### blockしないstderr診断（Issue #435）

次の2つは **`decision: block` を伴わず stderr にだけ出る**運用診断で、上表の
`POST_AUDIT_INTEGRITY_ERROR/<code>` とは別物である。監査証跡の劣化を運用者へ知らせるための
信号であって、merge可否の判定には使わない。

| 行 | 意味 |
|---|---|
| `AUDIT_ROTATION_SKIPPED/<code>` | 件数ローテーションを見送った。`<code>` は上表と同じ固定語彙 |
| `AUDIT_ROTATED removed=<n>` | 件数ローテーションで `<n>` 行を切り詰めた |
| `AUDIT_UNPARSABLE_LINES_SKIPPED count=<n>` | permit走査で壊れた行を `<n>` 件読み飛ばした（completionを書けた場合はレコードの `skipped_unparsable_lines` 側に載る） |

## 運用確認

両harnessでproject hookをtrust/enabledにし、`/hooks` とdebug logでregistrationとactual fireを
確認する。Actions statusはprimary allow根拠ではなく、GitHub Freeのstandard API以外の有料
serviceは使用しない。
