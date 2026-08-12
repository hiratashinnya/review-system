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
| 成功判定 | HTTP `2xx`（本 endpoint は成功時 `200` を返す） |
| Save responses | 有効（失敗時の切り分け用。応答本文に機微情報は含まれないことを確認済み） |

`<FINE_GRAINED_PAT>` はプレースホルダであり、実際の値は §3 で発行する PAT に置き換える。
この値を本ドキュメント・commit・PR・Issue コメントのいずれにも平文で残さないこと。

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

## 4. 疎通確認の方法

### 4.1 GitHub 側の起動実績を見る

```
gh run list --workflow=blocker-snapshot.yml --limit 10 --json event,createdAt,conclusion
```

`event=workflow_dispatch` の行が5分間隔前後で並んでいれば外部 cron が機能している。
`event=schedule` の行しかない場合は外部 cron が止まっている（PAT 失効・cron-job.org 側の障害等）。

### 4.2 snapshot の鮮度を直接見る

```
git fetch origin blocker-snapshot
git show origin/blocker-snapshot:snapshot.json | head -c 120
date -u +%Y-%m-%dT%H:%M:%SZ
```

`generated_at` と現在時刻の差が10分以内であることを確認する。

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
