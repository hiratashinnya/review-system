# blocker-gate CLI contract

`blocker_gate` は Issue-start と PR-merge が共有する read-only dependency resolver である。
managed Issue dispatch での interception と、独立した branch-source policy の実行点は
[`issue-start-and-branch-source.md`](issue-start-and-branch-source.md) を参照する。
native `blocked-by` と parent/sub-issue を正本とし、relation、Issue、waiver を変更しない。
policy version は `1.0`、stdout schema は `blocker-gate-result/v1` で固定する。

## Commands

```text
python3 -m blocker_gate issue --repository OWNER/REPO --number ISSUE
python3 -m blocker_gate pr --repository OWNER/REPO --number PR --merge-method merge|rebase|squash
python3 -m blocker_gate evaluate --snapshot PATH
```

`issue` は GitHub REST API `2026-03-10` で Issue本体、blocked-by、parent、sub-issue の
全pageを読み、対象Issueのdependency/closureを評価する。認証は `GH_TOKEN`、次に
`GITHUB_TOKEN`、最後に `gh auth token --hostname github.com` の既存資格情報を参照する。
`gh` が不在・未認証・timeout・空/異常応答の場合は匿名readを試す。tokenはAPIの
`Authorization` headerにだけ設定し、tokenやAuthorization headerは出力しない。

`pr` は GraphQL `closingIssuesReferences` を全cursor取得し、同じcore evaluatorへ渡す。
default branchへ届くmerge/rebase/squash messageの厳密な再構築は #298 のcollector接続責務であり、
そのsourceが未接続の状態では `ERROR/MESSAGE_SOURCE_INCOMPLETE` でfail-closeする。
non-default baseはclosing effectを持たないのでclosing setを空にする。

`evaluate` は `blocker-gate-snapshot/v1` fixture/collector出力をoffline評価する。これはunit/integration
testと将来の入口adapterが同じcoreを使用するための境界であり、waiverやrelationを保存する入口ではない。

## Output and exit

stdoutはUTF-8 control JSONを一件だけ出し、stderrは
`blocker-gate RESULT PRIMARY_REASON OWNER/REPO#NUMBER` の一行要約を出す。

| result | exit | permit |
|---|---:|---|
| `ALLOW` | 0 | `permit_issued=true` |
| `BLOCK` | 10 | `permit_issued=false` |
| `ERROR` | 20 | `permit_issued=false` |

API失敗、権限不足、partial response、pagination未完走、cycle、identity/contract不整合を
空集合やALLOWへ変換しない。argparseの用法エラーだけは標準のexit 2でありcontrol JSONを出さない。

runtime schemaは `blocker_gate/schemas/blocker-gate-result-v1.json` に置く。waiver適用済みfindingは
`waiver_evidence` に waiver ID、policy/waiver blob SHA、approval commit、期限を保持する。
Issue/PR command は open blocker がある場合だけ current default head の policy/waiver blob、
waiver変更commitの署名・ancestor、適用rulesetをfresh readし、resolver内でstrict parseと
`verify_waiver`を通過した候補だけを適用する。任意callbackのmappingはpermit根拠にしない。
waiverの作成、更新、承認、削除、失効は #299 の責務であり、このCLI/libraryにはwrite APIがない。
