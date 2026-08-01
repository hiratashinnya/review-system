# GitHub blocker gate API・無料構成 spike

- 対象: Issue #294（親 #293、handoff 先 #295）
- 実測日: 2026-08-01
- 対象 repository: `hiratashinnya/review-system`
- production gate の実装: **この spike では行わない**

## 1. 結論

採用できる read model は次の組み合わせである。

1. blocked-by / blocking と parent / sub-issue は REST API を正本として全 page を読む。GraphQL の `Issue.blockedBy` / `blocking` / `parent` / `subIssues` も同じ live relation を返したが、REST は status code、`Link`、API version を明示しやすい。
2. PR の close 候補は GraphQL `PullRequest.closingIssuesReferences` を cursor pagination して読む。default branch 以外を base にする PR では closing keyword が無効になり、この connection も空になった。
3. PR merge 後の判定は、close-set 内の Issue を仮想的に `CLOSED` としてから blocker と closure invariant を評価できる。同一 PR が blocker と blocked Issue を共に close する場合も同じ規則で扱える。
4. public repository の repository ruleset、GitHub Actions、standard GitHub-hosted runner は GitHub Free で利用できる。外部 SaaS、paid App、常駐 server は不要である。

ただし、**GitHub Actions だけでは native relation 変更直後の required check 再評価を保証できない**。`issue_dependencies` と `sub_issues` は Webhook event としては存在するが、GitHub Actions の workflow trigger 一覧には存在しない。`schedule` で open PR を再検査し commit status を上書きする案は最短5分かつ遅延・drop があり、成功済み status と relation 変更の間に race window が残る。

したがって #295 は、次のいずれかがオーナーに確定されるまで「relation 変更を即時反映する merge gate」を実装へ渡してはならない。

- Webhook receiver / GitHub App 等、`issue_dependencies` と `sub_issues` を受けて PR head status を失効させる経路を scope に追加する。
- bounded polling で残る最大 staleness と schedule の遅延/dropを明示的に受容する。
- blocker relation が安定した後に専用の trusted workflow を手動再実行する運用を受容する。この案は「記憶に頼らない」という #293 の目的を完全には満たさない。

merge queue は現在の候補ではない。この repository は User 所有であり、GitHub の merge queue は organization 所有 repository に限られる。organization への repository 移管は無料構成を維持できる可能性があるが、repository identity と運用主体を変える外部条件なので、オーナーの明示判断なしに前提にしない。

本 spike の推奨は、issue-start gate と resolver の設計は進める一方、PR gate の「race がない」という acceptance は上記判断まで停止することである。

## 2. 証拠の区分

| 区分 | 意味 |
|---|---|
| 実測 | 対象 repository の live API / 履歴から確認した |
| 仕様確認 | GitHub 公式 documentation で確認したが、この repository では該当 fixture がない |
| 未実測 | production relation、branch、Issue を調査のためだけに変更しないと再現できない。推測で PASS にしない |

公式資料:

- [REST API endpoints for issue dependencies](https://docs.github.com/en/rest/issues/issue-dependencies)
- [REST API endpoints for sub-issues](https://docs.github.com/en/rest/issues/sub-issues)
- [Linking a pull request to an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue)
- [Webhook events and payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads)
- [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- [Use `GITHUB_TOKEN` for authentication in workflows](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token)
- [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- [Managing rulesets for a repository](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/managing-rulesets-for-a-repository)
- [GitHub-hosted runners reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
- [Merging a pull request with a merge queue](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/merging-a-pull-request-with-a-merge-queue)
- [Dependabot on GitHub Actions](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-on-actions)

## 3. live repository baseline

| 項目 | 実測値 | 判定 |
|---|---|---|
| visibility / default branch | public / `main` | Free の repository ruleset と standard runner を利用可能 |
| owner | `hiratashinnya` / `type=User` | 現 repository では merge queue を利用不可 |
| 実測 token の repository permission | admin / maintain / push / triage / pull | owner PAT での probe。`GITHUB_TOKEN` の実測ではない |
| Actions | enabled、allowed actions=`all` | Actions 自体は利用可能 |
| default `GITHUB_TOKEN` | `read`、PR approval 不可 | workflow ごとに必要最小 permission を宣言する |
| ruleset | active `main`、rule は deletion / non-fast-forward、bypass なし | required status check は未設定 |
| `GET /rules/branches/main` | 空配列 | 現在の `main` に API が返す active rule はない。ruleset 名だけで有効範囲を推測しない |
| merge queue | open PR #234/#259/#260/#268 で `isMergeQueueEnabled=false` | 単なる未設定ではなく User 所有のため利用不可。organization 移管後だけ再検討可能 |
| fork PR | open PR はすべて同一 repository owner | fork / Dependabot の live 実測 fixture なし |

REST は明示した `X-GitHub-Api-Version: 2026-03-10` を response の `X-GitHub-Api-Version-Selected` で返した。version header を省略した `gh api` は `2022-11-28` を選択した。実装は version を固定し、変更を release note と probe で更新する。

## 4. API 対応表

### 4.1 relation

| 目的 | 採用 API | pagination | 最小 permission | live 結果 | 注意 |
|---|---|---|---|---|---|
| Issue が blocked by される集合 | `GET /repos/{owner}/{repo}/issues/{n}/dependencies/blocked_by` | `per_page` / `page`、max 100、`Link` を完走 | Issues: read。public は unauthenticated read も公式仕様上可能 | #295 → open #294 | `404` は不存在と非可視を区別できないため ERROR |
| Issue が blocking する集合 | `GET .../dependencies/blocking` | 同上 | Issues: read | #294 → open #295 | transitive closure は client が辿る |
| sub-issues | `GET .../issues/{n}/sub_issues` | 同上 | Issues: read | #293 → #294〜#299 の6件 | `per_page=1` で next/last Link と page 1/2 の別要素を実測 |
| parent | `GET .../issues/{n}/parent` | 単一 | Issues: read | #294 / #295 → #293 | 先に Issue 本体の `parent_issue_url` を読み、null の場合だけ parent なしとする |
| 一括 GraphQL read | `Issue.blockedBy`, `blocking`, `parent`, `subIssues` | cursor / `pageInfo` | resource の read permission | REST と同じ relation | partial `errors` を無視しない |

GraphQL schema introspection の live description も、`blockedBy` を「この Issue を block する Issue」、`blocking` を「この Issue が block する Issue」、`parent`、`subIssues` と定義していた。

直接 relation だけを API の意味とし、推移 closure と cycle detection は resolver の責務にする。全 node を `(repository node id, issue node id)` で識別し、訪問中 node への再入を cycle として fail-close する。

### 4.2 PR close-set

REST に PR の自動 close 集合を直接返す endpoint はない。GraphQL の次の connection を採用候補とする。

```graphql
pullRequest(number: $number) {
  baseRefName
  headRefOid
  closingIssuesReferences(first: 100, after: $cursor) {
    nodes { id number state repository { nameWithOwner } }
    pageInfo { hasNextPage endCursor }
  }
}
```

schema description は `closingIssuesReferences` を “List of issues that may be closed by this pull request” としており、**確定した merge transaction の close-set とは表現していない**。このため connection の完走に加えて、次を policy として固定する必要がある。

- base が repository の現在の default branch と一致すること。GitHub 公式仕様では closing keyword は default branch を target にするときだけ解釈される。
- PR description での closing keyword または GitHub の manual link を許容対象とする。
- commit message の closing keyword も default branch 到達時に Issue を close できる一方、公式仕様ではその commit を含む PR は linked PR として表示されない。close-set の唯一の取得元にできないため、#295 では「commit message での auto-close を禁止して検出時は fail」または「全 commit を pagination して別途構文解析」のどちらかを確定する。推奨は前者である。
- cross-repository Issue は `repository.nameWithOwner` を保持する。現在の repository-scoped `GITHUB_TOKEN` で読めない private repository が1件でもあれば ERROR とする。
- `hasNextPage=true` のまま終了、null、GraphQL top-level / partial error は ERROR とする。

live 比較:

| PR | base | body の relation | `closingIssuesReferences` | 状態 |
|---|---|---|---|---|
| #259 | `main` | `Closes #290` | open #290 | 実測 |
| #260 | `claude/agy-delegate-gate-fix` | `Closes #291` | 空 | non-default branch では keyword が無効であることを実測 |
| #268 | `main` | `Closes #292` | open #292 | 実測 |
| #234 | `main` | `Refs #288` / `Refs #217` | 空 | `Refs` は close-set ではないことを実測 |
| #235（merged） | `main` | `Closes #224` | closed #224 | merged at と Issue closed at が `2026-07-18T19:52:25Z` で一致 |

PR #235 は PR body と commit message の両方に `Closes #224` があるため、commit-only semantics の分離 fixture にはならない。

### 4.3 同一 PR の post-merge 仮想状態

次の順序なら同一 PR で blocker と blocked Issue を close するケースを扱える。

1. PR identity、default branch、head SHA を読む。
2. close-set を全 page 取得する。
3. close-set の各 Issue について blocker と sub-issue graph を全 page 取得する。
4. close-set 内 node の state だけを仮想的に `CLOSED` にする。
5. 仮想状態で blocker rule と parent closure invariant を評価する。
6. PR の base / head SHA / updated timestamp と root relation summary を再読し、変化していれば結果を破棄して再試行する。
7. 同じ head SHA にだけ結果を報告する。

これは判定アルゴリズムとして実装可能だが、複数 API response に transaction snapshot はない。手順6は race を狭めるだけで、relation が status 成功後に変わる race は残る。

## 5. event / 再評価表

| 変化 | GitHub event | Actions で直接 trigger | 採用可否 |
|---|---|---|---|
| PR open / reopen / head update | `pull_request` / `pull_request_target`: `opened`, `reopened`, `synchronize` | 可 | 再評価する |
| PR body / base update | `pull_request` / `pull_request_target`: `edited` | 可 | base、body、head SHA を API から再読する |
| auto-merge / queue 操作 | PR の `auto_merge_*`, `enqueued`, `dequeued` | 可 | 補助 trigger。最終判定の代替ではない |
| merge queue check | `merge_group: checks_requested` | 可 | Actions event 自体は存在するが、現 repository は User 所有なので queue を利用不可 |
| 同一 repository の Issue close / reopen | `issues: closed`, `reopened` | 可 | blocker state 変更を再評価できる。ただし workflow は default branch に存在する必要あり |
| 別 repository の blocker close / reopen | source repository の `issues` | この repository では**不可** | target repository の workflow は起動しない。bounded polling または両 repository を購読する外部 Webhook/App が必要 |
| blocked-by add/remove | Webhook `issue_dependencies` | **不可** | Webhook event は存在するが Actions trigger 一覧にない |
| parent/sub-issue add/remove | Webhook `sub_issues` | **不可** | 同上 |
| 定期監査 | `schedule` | 可 | 最短5分。遅延/drop、public repo 60日無 activity で disable があるため保証には使えない |
| operator 再検査 | `workflow_dispatch` | 可 | runbook には使えるが、人の記憶に依存するため主経路にはしない |
| 外部 receiver から通知 | `repository_dispatch` | 可 | receiver が別途必要。この spike の無料・repository-only 境界外 |

対象 Issue #295 の timeline には live に `parent_issue_added`、`blocked_by_added`、`blocking_added` が記録されていた。relation 変更の監査証跡は REST timeline から読めるが、timeline entry 自体は required check の即時 trigger にはならない。

## 6. permission / trust boundary

### 6.1 resolver と workflow

| 操作 | workflow permission | 備考 |
|---|---|---|
| Issue relation / state read | `issues: read` | blocker、parent/sub-issue、timeline |
| PR metadata / commits read | `pull-requests: read` | base、head、body。GraphQL resource read にも必要 |
| repository default branch / commit read | `contents: read` | default branch と commit list の照合 |
| PR head に commit status を作成 | `statuses: write` | schedule / trusted event から `error|failure|pending|success` を上書きする場合。Checks API は不要 |
| Actions run の参照 | `actions: read` | run URL や再実行を resolver が扱う場合だけ |
| ruleset read | Metadata: read | public resource では unauthenticated read も可能 |
| ruleset create/update | Administration: write / repository admin | workflow の runtime token へ与えず、owner の一回限り設定に分離する |

現在の default `GITHUB_TOKEN` は read である。production workflow は `permissions:` を明記し、不要な `issues: write`、`pull-requests: write`、`checks: write`、secrets を与えない。

### 6.2 fork / Dependabot

fork と Dependabot は同じものとして扱わない。

| actor / event | workflow code | `GITHUB_TOKEN` / secrets | status 報告案 | 限界 |
|---|---|---|---|---|
| fork PR / `pull_request` | PR merge ref 側 | token は read-only、secrets なし | job 自体の check は出せるが、untrusted PR が workflow を変更し得るため security gate の正本にしない | 初回 contributor approval、conflict、skip 条件で未起動になり得る |
| fork PR / `pull_request_target` | trusted default branch | 必要最小 permission を明示可能 | `statuses: write` だけを付け、API metadata を再読して検証済み head SHA に status を作る候補 | PR head を checkout / execute しない。title/body を shell code にしない |
| Dependabot PR / `pull_request` | PR merge ref 側 | read-only、Actions secrets なし | write status に依存不可 | Dependabot secrets と通常 secrets は別 |
| Dependabot PR / `pull_request_target` | trusted default branch | GitHub 公式制約により read-only、secrets なし。この制約は別 actor の re-run にも残る | `statuses: write` に依存不可 | 通常 fork の trusted write 経路と同一視しない |

Dependabot で成立し得る trusted write 経路の候補は、read-only の PR workflow 完了を `workflow_run` で受ける default-branch workflow、または `schedule` / `workflow_dispatch` である。`workflow_run` は先行 workflow より強い token / secrets を持てるため、次をすべて満たさない限り採用しない。

- untrusted head code、artifact、cache、script を実行しない。
- event の run id から repository、PR number、head SHA、actor を API で再取得し、status の付与先を束縛する。
- `workflow_run` は PR event が起きた時だけであり、blocker relation や cross-repository Issue state の変更を直接受けないと明記する。
- schedule は最短5分かつ遅延/drop/disable、manual は人の記憶への依存が残るため、どちらも即時保証ではない。

この repository に fork / Dependabot PR がないため、token downgrade、approval待ち、status の付与先は未実測である。#298 は production ruleset を有効にする前に disposable fixture で確認し、workflow が起動しない、status を書けない、または head SHA を一意に束縛できない場合は fail-close する。

### 6.3 merge queue

GitHub 公式仕様では、merge queue は organization 所有の public repository、または GitHub Enterprise Cloud を使う organization 所有 private repositoryで利用できる。`hiratashinnya/review-system` は User 所有の public repository なので、現状では **利用不可** であり採用案に含めない。

organization への repository 移管をオーナーが別途明示決定した場合だけ再評価する。その場合も、required check workflow は `merge_group: checks_requested` を含め、close-set を group 内 PR ごとに再構築して group SHA に結果を返す fixture が PASS するまで #298 を merge-ready にしない。移管前に merge queue を前提とする設計は停止する。

## 7. GitHub Free 判定

| 構成要素 | 無料可否 | 根拠 / 条件 |
|---|---|---|
| repository ruleset | 可 | public repository は GitHub Free で利用可能 |
| required status check | 可 | repository ruleset の branch rule。status/check 名は一意にする |
| GitHub Actions | 可 | public repository の standard GitHub-hosted runner は free / unlimited |
| REST / GraphQL read | 可 | `GITHUB_TOKEN` / existing `gh` で可能。API rate limit と pagination は守る |
| scheduled audit | 可 | ただし遅延/drop/disable があり厳密保証には不可 |
| GitHub App registration | App 自体は構成可能 | Webhook receiver の稼働場所は repository-only 構成に含まれず、本 spike では採用しない |
| external SaaS / paid required workflow | 不可 | #294 の調査境界外。導入しない |

現在の `ruleset 18482582` には required status check がない。#298 で workflow が直近7日以内に一度成功し、fork / merge_group fixture を通した後、owner が expected source と bypass policy を確認してから追加する。

## 8. 障害・曖昧・race の扱い

### 8.1 fail-close 条件

次のどれかなら ALLOW を返さない。

- REST が `403`, `410`, `429`, `5xx`、timeout、invalid JSON を返す。
- relation list または存在確認済み resource の REST が `404` を返したのに「relation なし」と判定する。parent は Issue 本体の `parent_issue_url=null` のときだけ「なし」とし、非 null なのに parent endpoint が `404` なら ERROR とする。
- GraphQL response に top-level または partial `errors` がある。
- cursor / `Link` を完走できない、同じ cursor/page を再訪する、件数上限を超える。
- cross-repository node を読めない、transfer / delete で repository identity が変わる。
- cycle、self relation、重複 node の矛盾、state の未知値を検出する。
- PR base が現在の default branch でない、head SHA が評価中に変わる。
- GraphQL close 候補と許可した closing syntax の結果が一致しない。
- fork / Dependabot / merge_group の未検証経路が production で現れる。
- cross-repository blocker を初期 policy で許可していない、または source repository の state change を購読・pollできない。

retry は `Retry-After` と rate-limit header を尊重した有限回に限定する。retry 上限後は ERROR とし、最後の成功 cache を ALLOW に再利用しない。

### 8.2 残る race window

| race | 無料構成での緩和 | 閉じ切れるか |
|---|---|---|
| traversal 中に relation/state が変わる | root summary / ETag / PR head を最後に再読 | いいえ。複数 endpoint に snapshot transaction がない |
| check success 後に blocker が追加される | relation webhook receiver、または最短5分 polling で status を failure に上書き | Actions-only polling では閉じない |
| check success 後に blocker が reopen される | `issues: reopened` で再評価 | workflow 起動から status 更新まで窓がある |
| cross-repository blocker が close / reopen される | target repository から定期 polling、または source/target を購読する外部 Webhook/App | target の Actions は source の `issues` event で起動しないため Actions-only の即時保証は不可 |
| Dependabot PR を trusted workflow で再評価する | `workflow_run` / schedule / manual から API metadata だけを再読 | relation change の直接 trigger ではなく、schedule/manual の限界も残る |
| organization 移管後の merge queue 入場後に relation が変わる | `merge_group` 評価 + relation event で group status 失効 | 現 repository では利用不可。移管後も relation event receiver がなければ閉じない |
| PR body/base/head が評価後に変わる | PR event と head SHA 束縛、ruleset は最新 SHA の status を要求 | relation race とは別に管理可能 |
| schedule が遅延/drop/disable | cron を時の0分からずらす、監査で last-run age を検査 | 定期処理自体の不実行は完全には閉じない |

required status check は「特定 SHA で過去に成功した」ことを保持する。Issue relation 変更に SHA 変更はないため、status の freshness や TTL を ruleset だけで要求できない。

## 9. #295 への handoff

### 9.1 採用案

1. relation の正本は native REST dependency / sub-issue endpoint。本文の `Blocked by:` 等は警告にのみ使う。
2. resolver は全 pagination、transitive traversal、cycle detection、repository identity、closed/open state を一つの Result にする。API error と policy block を区別するが、どちらも exit non-zero とする。
3. PR close 候補は `closingIssuesReferences` + default branch + head SHA で束縛し、post-merge 仮想状態で blocker と closure invariant を評価する。
4. commit-message closing keyword は禁止を推奨する。許容する場合は GraphQL connection だけを close-set と呼ばない。
5. PR workflow は trusted default branch の code だけを実行し、PR head を checkout/execute しない。fork input は data としてのみ処理する。
6. API ambiguity、permission不足、unknown event、incomplete pagination、cycle は fail-close。前回成功 cache への fallback は禁止する。
7. Issue-start gate は実行開始のたびに live API を読むため、PR relation invalidation の判断を待たず設計可能である。
8. PR merge gate は relation event の即時 invalidation方式が確定するまで「race-free」としない。
9. cross-repository blocker は初期 policy では ERROR を推奨する。許可するには source repository の close/reopen を受ける外部 Webhook/App、または owner が受容した bounded polling を必須にする。
10. merge queue は現 repository の候補から除外する。organization 移管がオーナー決定された場合だけ別 fixture で再評価する。

### 9.2 #295 の停止条件

- `issue_dependencies` / `sub_issues` を status 失効へ接続する手段を決めず、Actions の `issues` event が relation 変更でも発火すると仮定している。
- 5分 schedule を即時 gate と同等に扱う、または schedule の成功 status に TTL があると仮定している。
- commit message closure、manual link、cross-repository closure の扱いが未定である。
- fork / Dependabot と merge queue の fixture がないまま required check を active にする。
- Dependabot の `pull_request_target` で `statuses: write` が使えると仮定する、または privileged `workflow_run` で untrusted head/artifact/cache を実行する。
- cross-repository blocker を許容しながら、source repository の close/reopen がこの repository の `issues` workflow を起動すると仮定する。
- User 所有の現 repository で merge queue を有効化できると仮定する。organization 移管は別のオーナー判断・移行計画なしに前提化しない。
- ruleset の required check source、bypass actor、strict policy が owner 確認されていない。merge queue policy は organization 移管後だけ対象にする。
- race の受容主体と最大許容 staleness が記録されていない。

## 10. 再現手順（read-only）

secret や token value は出力・保存しない。以下は repository root から実行する。

### 10.1 REST の全 page

```bash
# direct blocker
rtk proxy gh api \
  -H 'X-GitHub-Api-Version: 2026-03-10' \
  repos/hiratashinnya/review-system/issues/295/dependencies/blocked_by \
  --paginate --jq 'map({number,state,title,repository_url})'

# per_page=1 にして Link を gh に最後まで追わせる。各 page の1件を出力する
rtk proxy gh api --method GET \
  repos/hiratashinnya/review-system/issues/293/sub_issues \
  -f per_page=1 --paginate \
  --jq '.[] | [.number,.state] | @tsv'

# Link header 自体の確認
rtk proxy gh api --include --method GET \
  repos/hiratashinnya/review-system/issues/293/sub_issues \
  -f per_page=1 -f page=1

# timeline relation events
rtk proxy gh api \
  -H 'Accept: application/vnd.github+json' \
  repos/hiratashinnya/review-system/issues/295/timeline \
  --paginate \
  --jq 'map({event,created_at,actor:.actor.login})'

# ruleset / Actions baseline
rtk proxy gh api repos/hiratashinnya/review-system/rulesets/18482582 \
  --jq '{id,name,enforcement,conditions,rules,bypass_actors}'
rtk proxy gh api repos/hiratashinnya/review-system/actions/permissions/workflow
```

期待 evidence:

```text
#295 blocked_by: #294 open
REST sub_issues: 294, 295, 296, 297, 298, 299（6行）
page=1 Link: rel="next" page=2、rel="last" page=6
timeline: parent_issue_added / blocked_by_added / blocking_added
API version header: X-GitHub-Api-Version-Selected: 2026-03-10
```

### 10.2 GraphQL cursor の全 page

`gh api graphql --paginate` が使う変数名を `$endCursor` にし、`pageInfo` を必ず query に含める。`first:1` で6 pageを強制する。

```bash
rtk proxy gh api graphql --paginate \
  -f query='query($endCursor: String) {
    repository(owner:"hiratashinnya", name:"review-system") {
      issue(number:293) {
        subIssues(first:1, after:$endCursor) {
          nodes { number state }
          pageInfo { hasNextPage endCursor }
        }
      }
    }
  }' \
  --jq '.data.repository.issue.subIssues.nodes[] | [.number,.state] | @tsv'
```

期待 evidence は `294 OPEN` から `299 OPEN` までの6行である。2026-08-01 の再実行で REST と同じ順序・件数を確認した。

PR close 候補も同じ cursor 契約で読む。

```bash
rtk proxy gh api graphql --paginate \
  -f query='query($endCursor: String) {
    repository(owner:"hiratashinnya", name:"review-system") {
      pullRequest(number:259) {
        baseRefName
        closingIssuesReferences(first:1, after:$endCursor) {
          nodes { number state repository { nameWithOwner } }
          pageInfo { hasNextPage endCursor }
        }
      }
    }
  }' \
  --jq '.data.repository.pullRequest.closingIssuesReferences.nodes[] |
        [.repository.nameWithOwner,.number,.state] | @tsv'
```

期待 evidence:

| query | expected |
|---|---|
| PR #259 | `hiratashinnya/review-system`, #290, `OPEN` |
| PR #260 | 0件。base が non-default |
| PR #268 | #292, `OPEN` |
| PR #234 | 0件。`Refs` だけ |

### 10.3 schema / repository capability

GraphQL field の description と repository owner type を read-only で確認する。

```bash
rtk proxy gh api graphql \
  -f query='query {
    __type(name:"PullRequest") { fields { name description } }
    repository(owner:"hiratashinnya", name:"review-system") {
      owner { __typename login }
    }
  }' \
  --jq '{owner:.data.repository.owner,
         closing:(.data.__type.fields[] |
           select(.name=="closingIssuesReferences"))}'
```

期待 evidence は owner が `User` / `hiratashinnya`、field description が `List of issues that may be closed by this pull request` である。User 所有という結果と GitHub 公式 availability を組み合わせ、merge queue は現 repository で利用不可と判定する。

### 10.4 未実測 fixture の再現計画

次は現在の production Issue / relation / repository ownership を変更しないと分離実測できないため、この PR では実行しない。実行にはオーナー承認と disposable repository を必須にし、production の #293〜#299 を fixture に転用しない。

| 未実測項目 | disposable fixture | 手順 | expected evidence / 合否 |
|---|---|---|---|
| closed blocker | 同一 disposable repo の Issue A/B | B blocked-by A を作り、A open時とclose後を全page取得 | open時は BLOCK、close後は ALLOW。relation edge は残る |
| cycle / self | disposable Issue A/B/C | A→B→C の後で C→A と self edge を API で試す | GitHub が `422` で拒否するか、作成できるなら resolver が cycle として ERROR。どちらも response status/bodyをsecret除外で保存 |
| same-PR multiple close | disposable PR + Issue A/B | default branch向け PR bodyで両 Issueをclose候補にする。mergeは別承認 | `closingIssuesReferences` が A/B の2件。post-merge仮想状態で同じPR内blockerをCLOSED扱い |
| commit-only close | disposable PR + Issue A | PR bodyにkeywordを置かずcommit messageだけに置く | GraphQL connectionと実merge closeの差を記録。policyが禁止なら merge前にERROR |
| permission不足 / hidden private resource | disposable private repo + Issues readなし fine-grained token | relation readを行う | `403` または情報秘匿の `404`。ALLOWへ変換しない。token valueは保存しない |
| API failure / pagination中断 | resolver fake transport または fault-injection test | page 2でtimeout/5xx/invalid JSON/同一cursorを返す | ERROR、最後の成功cacheを使わない、status successを作らない |
| fork PR | disposable fork PR | `pull_request` と `pull_request_target` の token permission、approval、head SHAを記録 | head code非実行。trusted pathだけが検証済みSHAへ結果を付ける |
| Dependabot PR | Dependabot有効の disposable repo | `pull_request` / `pull_request_target` / `workflow_run` のpermissionとstatus付与先を記録 | PR系tokenはread-only。trusted `workflow_run` はuntrusted artifact/codeを実行せず、APIで束縛したSHAだけに書く |
| cross-repo blocker | disposable source/target repo | source blockerをclose/reopenし、target workflow run履歴を観察 | target の `issues` workflowは起動しない。polling時だけ検出、または外部Webhook/Appで即時失効 |
| merge queue | organization ownershipへ移した disposable public repo | queue有効化後に `merge_group` payload/group SHAを記録 | **現 User-owned repoでは実行不可**。organization移管のowner決定なしでは着手しない |

fixture evidence は request の endpoint/variables、HTTP status、secretを除いたresponse要約、workflow run URL、対象 repository/Issue/PR URL、実行日時を一組として残す。未実行の行は PASS にしない。

参考として、単発 query の GraphQL 形は次のとおりである。

```graphql
query Spike {
  repository(owner: "hiratashinnya", name: "review-system") {
    issue(number: 295) {
      number
      state
      parent { number state }
      blockedBy(first: 100) {
        nodes { number state }
        pageInfo { hasNextPage endCursor }
      }
      blocking(first: 100) {
        nodes { number state }
        pageInfo { hasNextPage endCursor }
      }
    }
    pullRequest(number: 259) {
      number
      baseRefName
      headRefOid
      closingIssuesReferences(first: 100) {
        nodes { number state repository { nameWithOwner } }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
  rateLimit { limit remaining cost resetAt }
}
```

## 11. acceptance 状態

| #294 acceptance | 状態 | 根拠 / 未実測理由 |
|---|---|---|
| open/closed blocker、transitive、cycle、pagination | 一部実測 | open / transitive / pagination は live 実測。closed / cycle は production relation を調査のために変更しないため未実測。disposable fixture を owner 承認後に実行する |
| PR closing Issue と default branch / auto-close | 一部実測 | main / non-default の connection 差と過去の merge-close timestamp は実測。commit-only と同一PR複数closeの live fixture は未実測 |
| relation 変更後の required check 再評価 | 制約を実測・仕様確認 | timeline event は実測。Webhook は存在、Actions direct trigger は不存在。厳密再評価は Actions-only では保証不能 |
| fork / Dependabot、merge_group、API障害、権限不足 | 仕様確認 / 未実測 | repository に fixture なし。merge queue は User 所有の現 repoでは利用不可。公式制約、disposable fixture、fail-close 条件を記録した |
| 無料構成、不可能な保証、race | 完了 | Free 可否と Actions-only の不可能保証、TOCTOU を明示 |
| #295 へ採用案 / 停止条件 | 完了 | 本文 §9 |

未実測項目を PASS とみなさず、後続 Issue の fixture と owner decision に明示的に渡す。PR #300 は `Refs #294` とし、#294 を自動 closeせず、#295 の native blockerを解除しない。
