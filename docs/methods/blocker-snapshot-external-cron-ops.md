# blocker-snapshot: 外部 cron（cron-job.org）運用手順

- 対象: Issue #363（発端）、Issue #345（`blocker-snapshot` の元設計）、PR #359（snapshot 機構の実装）
- 関連正本: `.github/workflows/blocker-snapshot.yml`、`docs/methods/blocker-gate-pre-use-policy.md` §3.3
- 実施者: 本ドキュメントの手順（cron-job.org のアカウント作成・PAT 発行・ジョブ登録）は
  **リポジトリオーナーが Console 上で手動実施する**。実装エージェント（`issue-implementer` 等）は
  実施しない・実施できない（GitHub 外のサービスの認証情報を扱うため）。

## 1. 背景（なぜこの手順が必要か）

`blocker-snapshot.yml` は `blocker_gate` pre-use gate（`docs/methods/blocker-gate-pre-use-policy.md`
§3.3）が到達不能環境で読む `snapshot.json` を、孤立ブランチ `blocker-snapshot` へ publish する。
gate はこの snapshot の `generated_at` が **10分以内**でなければ fail-close する。

Issue #363 の実測により、GitHub の `schedule: "*/5 * * * *"` は「5分ごとに動く」ことを保証しない
（実測 74〜104 分間隔）ことが判明した。したがって **`schedule` だけでは staleness 上限を満たせない**。

オーナー確定の対策は、**外部 cron サービス（cron-job.org）から GitHub の `workflow_dispatch` REST API
を5分間隔で叩く**構成である。`schedule` はこの外部 cron が止まったときの保険として残す
（`.github/workflows/blocker-snapshot.yml` の `on:` ブロックのコメント参照）。

## 2. cron-job.org のジョブ設定

Console（<https://cron-job.org/en/>）でログイン後、次の内容でジョブを作成する。

| 設定項目 | 値 |
|---|---|
| Title | `blocker-snapshot dispatch (review-system)` |
| URL | `https://api.github.com/repos/hiratashinnya/review-system/actions/workflows/blocker-snapshot.yml/dispatches` |
| Request method | `POST` |
| Schedule | 毎時 `0,5,10,15,20,25,30,35,40,45,50,55` 分・毎時・毎日・毎月・毎曜日（＝5分間隔）／timezone `UTC` |
| Headers | `Accept: application/vnd.github+json`<br>`Authorization: Bearer <FINE_GRAINED_PAT>`<br>`X-GitHub-Api-Version: 2026-03-10`<br>`Content-Type: application/json` |
| Body | `{"ref":"main"}` |
| 成功判定 | HTTP `2xx`（[GitHub REST API docs: Create a workflow dispatch event](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event) によれば成功時は `204 No Content`。実装エージェントは外部 API を実際に叩いて確認できないため未実測——`2xx` 全体を成功とみなす設定にしておけば具体的な code の違いは吸収される） |
| Save responses | 有効（失敗時の切り分け用。上記 endpoint は成功時 body を返さず、失敗時も GitHub の標準エラー JSON（`message`/`documentation_url` 程度）を返す想定であり、Authorization header 等の機微情報が応答本文に含まれる仕様ではない。ただしこれも実装エージェントが実際に応答を確認したものではなく未実測——気になる場合は §4.3 の実行履歴でオーナーが実際の応答本文を確認すること） |

`<FINE_GRAINED_PAT>` はプレースホルダであり、実際の値は §3 で発行する PAT に置き換える。
この値を本ドキュメント・commit・PR・Issue コメントのいずれにも平文で残さないこと。

> **他のワークフローへ本ジョブ設定を流用しないこと。** 上表の Body `{"ref":"main"}` は
> `inputs` を含まない。`workflow_dispatch` の入力で挙動が変わるワークフローにこの body を
> 向けると、入力はワークフロー定義の既定値に落ちる。実例＝`project-status-sync.yml` は
> `inputs.apply` が `true` のときだけ Project へ書き込むため、この body を流用すると
> 常用運転が永久に dry-run になる（Issue #470）。同ワークフロー用の手順は
> `docs/methods/project-status-sync-external-cron-ops.md` にある。

### API で作る場合の等価な設定（参考・Console 操作の代替）

```bash
curl -X PUT \
     -H 'Content-Type: application/json' \
     -H 'Authorization: Bearer <CRONJOB_ORG_API_KEY>' \
     -d '{
       "job": {
         "title": "blocker-snapshot dispatch (review-system)",
         "url": "https://api.github.com/repos/hiratashinnya/review-system/actions/workflows/blocker-snapshot.yml/dispatches",
         "enabled": true,
         "saveResponses": true,
         "requestMethod": 1,
         "extendedData": {
           "headers": {
             "Accept": "application/vnd.github+json",
             "Authorization": "Bearer <FINE_GRAINED_PAT>",
             "X-GitHub-Api-Version": "2026-03-10",
             "Content-Type": "application/json"
           },
           "body": "{\"ref\":\"main\"}"
         },
         "schedule": {
           "timezone": "UTC",
           "expiresAt": 0,
           "hours": [-1],
           "mdays": [-1],
           "minutes": [0,5,10,15,20,25,30,35,40,45,50,55],
           "months": [-1],
           "wdays": [-1]
         }
       }
     }' \
     https://api.cron-job.org/jobs
```

`requestMethod: 1` は cron-job.org REST API の `RequestMethod` enum で `POST` を表す
（`0`=GET / `1`=POST / `2`=OPTIONS / `3`=HEAD / `4`=PUT / `5`=DELETE / `6`=TRACE / `7`=CONNECT / `8`=PATCH）。

`<CRONJOB_ORG_API_KEY>` は cron-job.org の Console → Settings で発行する API キー。**IP 制限を掛ける**
ことが cron-job.org 公式に強く推奨されている。

## 3. fine-grained PAT の作成条件

GitHub の Settings → Developer settings → Personal access tokens → Fine-grained tokens で、次の条件で
作成する。

| 項目 | 値 | 理由 |
|---|---|---|
| Resource owner | `hiratashinnya` | |
| Repository access | **Only select repositories → `review-system`** | 他リポジトリへ権限を波及させない |
| Permissions | **Actions: Read and write** のみ | `POST .../dispatches` endpoint が公式に要求する最小権限。他の permission は付与しない |
| Expiration | 有効期限を設定する（無期限にしない） | 期限切れ時は cron-job.org 側で `401` になる。これは gate を止める方向にしか働かない（下記 §5） |

発行した値はそのまま cron-job.org のジョブ設定（§2 の `Authorization` header）に貼り付ける。
リポジトリ内のどのファイル・コミット・Issue/PR コメントにも平文で残さないこと。

### PAT 期限切れ時の挙動（意図した安全側の劣化）

1. cron-job.org のジョブが `401 Unauthorized` を受け取る（cron-job.org 側の実行履歴に記録される）。
2. `workflow_dispatch` による起動が止まる。`schedule`（実測 74〜104 分間隔）だけが残る。
3. `snapshot.json` の `generated_at` が staleness 上限（10分）を超え続ける。
4. 到達不能環境の gate は snapshot を読んでも fail-close する（`docs/methods/blocker-gate-pre-use-policy.md`
   §3.3「fail-close の非緩和」）。**ALLOW には倒れない。**

つまり PAT 期限切れは「気づかれないまま危険側に倒れる」のではなく「気づかれないまま安全側に倒れる」。
ただし `/issue-pipeline` がリモート環境で使えなくなるため、後述 §4 の疎通確認を定期的に行うこと。

### PAT 更新（rotation）手順

1. GitHub の Settings → Developer settings → Personal access tokens → Fine-grained tokens で、上表
   （Resource owner / Repository access / Permissions / Expiration）と同じ条件で新しい PAT を発行する。
2. cron-job.org の Console → 対象ジョブ（§2 の `blocker-snapshot dispatch (review-system)`）→
   Headers の `Authorization: Bearer <FINE_GRAINED_PAT>` を新しい値に差し替えて保存する。
3. §4.1・§4.2 の疎通確認を行い、次回 dispatch が成功し snapshot が更新されることを確認する。
4. 旧 PAT を GitHub の Settings → Developer settings → Personal access tokens で失効（revoke）する。

失効検知の頻度と担当:

- **頻度**: リポジトリオーナーが、少なくとも週1回、§4.1 の `gh run list --workflow=blocker-snapshot.yml
  --limit 10 --json event,createdAt,conclusion` を実行して確認する。`event=workflow_dispatch` の行が
  5分間隔で並んでいれば、その時点で PAT が有効であることも同時に確認できる（失効時は cron-job.org 側で
  `401` になり dispatch が来なくなる＝上記「PAT 期限切れ時の挙動」）。
- **担当**: 本ドキュメント冒頭「実施者」のとおり、cron-job.org・GitHub PAT はいずれも本リポジトリ外の
  認証情報であり実装エージェントは扱えないため、上記手順・疎通確認は**リポジトリオーナーが実施する**。
  発行時に設定した `Expiration` の日付をオーナー自身が追跡し、期限前に本節の手順で更新する
  （リポジトリ内に自動リマインダーの仕組みは無い）。

## 4. 疎通確認の方法

### 4.1 GitHub 側の起動実績を見る

```
gh run list --workflow=blocker-snapshot.yml --limit 10 --json event,createdAt,conclusion
```

`event=workflow_dispatch` の行が5分間隔前後で並んでいれば外部 cron が機能している。
`event=schedule` の行しかない場合は外部 cron が止まっている（PAT 失効・cron-job.org 側の障害等）。

**`conclusion` 列も見て `cancelled` を除外すること**: `.github/workflows/blocker-snapshot.yml` は
`concurrency.group: blocker-snapshot` と `cancel-in-progress: true` を設定しているため、runner の
キュー待ちが外部 cron の実効間隔（5分）を超えると、実行中の run が次の dispatch に cancel され、
publish されないまま連鎖する経路が理屈上ある（実測ではまだ観測されていない・Issue #363）。
`conclusion=cancelled` の run を「実行された」に数えると誤診断するため、`success` の run だけを
数えて間隔を確認する。`cancelled` が連続する場合は、キュー待ちが5分を超えている可能性があり、
snapshot が publish されない劣化条件（`.github/workflows/blocker-snapshot.yml` の
「既知の劣化条件」コメントを参照）に該当しうる。cancel-in-progress の設定自体は本ドキュメントの
時点では変更しない（是非はオーナー判断）。

### 4.2 snapshot の鮮度を直接見る

```
git fetch origin blocker-snapshot
git show origin/blocker-snapshot:snapshot.json | head -c 120
date -u +%Y-%m-%dT%H:%M:%SZ
```

`generated_at` と現在時刻の差が10分以内であることを確認する。

**policy_version bump 直後の注意**（`docs/methods/blocker-gate-pre-use-policy.md` §3.3「policy version
の扱い」）: `policy_version` を bump する PR が merge された直後は、`generated_at` が10分以内で新しく
見えても、その snapshot の中身がまだ bump 前の `policy_version` を含んでいることがある——snapshot は
`blocker_gate snapshot` を実行した時点のコード（`blocker_gate/model.py` の `POLICY_VERSION`）を埋め込む
ため、merge 後の次回 Actions 実行（外部 cron の5分間隔で通常は完了する）を待つまでは古い版のままである。
この窓では到達不能環境の gate は `blocker_gate/snapshot.py` が送出する `SNAPSHOT_POLICY_VERSION_MISMATCH`
により fail-close する。診断するときは `generated_at` の鮮度だけでなく、
`git show origin/blocker-snapshot:snapshot.json` の `policy_version` フィールドが現行の
`POLICY_VERSION` と一致しているかも確認すること。不一致であれば、次回の外部 cron dispatch（最大5分）
を待てば解消する。

### 4.3 cron-job.org 側の実行履歴を見る

cron-job.org の REST API `GET /jobs/<jobId>/history`（Console からも同等の履歴が閲覧できる）で、
実行間隔（jitter）とレスポンスコードを確認する。§2 で `Save responses: 有効` にしていれば、`401`
（PAT 失効）等の失敗もここで気づける。

## 5. 信頼モデル：この PAT は snapshot の内容を偽造できない

`docs/methods/blocker-gate-pre-use-policy.md` §3.3.1 の信頼モデル（snapshot 経路は gate の保証を
弱めない）は、書き手が Actions workflow のみであることを前提にしている。今回追加する外部 cron の
PAT はこの前提を変えない——**PAT が持つのは「生成を始めさせる引き金」だけ**であり、snapshot の
内容そのものを生成するのは常に Actions 上の workflow（GitHub の `GITHUB_TOKEN` で GraphQL から
取得）である。

漏洩時の最悪ケース:

| PAT でできること | gate への影響 |
|---|---|
| ワークフローを何度も起動する | snapshot が余計に更新されるだけ。判定は変わらない |
| ワークフローを無効化する／実行をキャンセルする | snapshot が古くなる → staleness 上限超過で gate が fail-close（安全側） |
| **snapshot の内容を書き換える** | **できない**。`Actions: Read and write` permission は `blocker-snapshot` ブランチへの
  `git push` 権限を含まない（GitHub API の Actions permission は workflow の実行制御であり、
  リポジトリ内容への書き込みは `Contents` permission の管轄）。加えて gate は
  origin 一致・schema・staleness・repository 一致をすべて検証する（policy §3.3.1） |

この構成で新たに増える権限は「gate を止める方向」にしか働かない。#345 で退けた「エージェントの
裁量で判定材料を取得する」方式とは信頼モデルが根本的に異なる（判定材料は常に Actions が機械的に
生成し、PAT はそれをいつ始めるかだけを制御する）。

## 6. 課金（無課金で完結）

- cron-job.org: 公式トップページに「from minute-by-minute to once in a year. Absolutely free.」と
  明記。分単位のスケジュールを含め無料。
- GitHub Actions: 本 repository は public のため実行時間の課金は発生しない（無料枠の上限自体が
  存在しない）。
- GitHub API 消費: 5分間隔で `POST .../dispatches` を叩くと 288 requests/日。fine-grained PAT の
  レート上限 5,000 requests/時 に対し十分収まる。

課金が発生する構成に切り替える場合は、実装前にオーナーの明示的な認可が必要（`CLAUDE.md`
「CI/外部サービス連携のコスト方針」）。本手順はその必要がない無課金構成である。

## 7. 未確認事項（cron-job.org 設定後に実測すること）

Issue #363 の受け入れ条件のうち、次はオーナーが cron-job.org を実際に設定した後でなければ検証
できない。実装エージェントはこの検証を代行できない。

- cron-job.org の実際の起動精度（jitter）。§4.3 の実行履歴 API と `gh run list` の突き合わせ
- 5分間隔で実際に `snapshot.json` の `generated_at` が10分以内に保たれ続けること
- 到達不能環境（Claude Code on the web 等）で `python3 -m blocker_gate issue` が実際に判定できること
- 同環境で `/issue-pipeline` から `issue-implementer` を dispatch でき、blocker がある Issue では
  従来どおり deny されること

これらは cron-job.org 設定完了後にオーナーまたは次の作業者が実測し、Issue #363 の受け入れ条件
チェックボックスを更新すること。
