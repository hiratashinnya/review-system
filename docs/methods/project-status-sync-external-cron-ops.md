# project-status-sync: 外部 cron（cron-job.org）運用手順

- 対象: Issue #470（本手順の発端）、Issue #460（`project_status_sync` の元設計）、
  Issue #363（GitHub 純正 `schedule` が cron 式どおりに発火しないという実測）
- 関連正本: `.github/workflows/project-status-sync.yml`、`project_status_sync/README.md`
- 姉妹手順: `docs/methods/blocker-snapshot-external-cron-ops.md`（`blocker-snapshot` 用。
  **body・cadence・失敗時の意味がすべて異なるので、設定をそのまま流用しないこと**＝§2.1）
- 実施者: 本ドキュメントの手順（cron-job.org のジョブ登録・PAT の確認/発行）は
  **リポジトリオーナーが Console 上で手動実施する**。実装エージェント（`issue-implementer` /
  `issue-fixer` 等）は実施しない・実施できない（GitHub 外のサービスの認証情報を扱うため）。

## 1. 背景（なぜ外部 cron が要るか）

`project-status-sync.yml` は GitHub Project「review-system Development」の `Status` を、
`blocker-snapshot` ブランチに publish 済みの `snapshot.json` から同期する（Issue #460）。
cadence は **20分**（`project_status_sync/README.md`「### GitHub Actions からの実行」）。

Issue #363 の実測により、GitHub の `schedule:` は cron 式どおりの間隔で発火しないことが
判明している（`*/5 * * * *` に対して実測 74〜104 分間隔）。したがって **`schedule: "*/20 * * * *"`
を置いただけでは20分 cadence は成立しない**。

`blocker-snapshot` と同じ対策——**外部 cron サービス（cron-job.org）から GitHub の
`workflow_dispatch` REST API を叩く**——を採る。純正 `schedule` は外部 cron が止まったときの
保険として残す（ワークフローの `on:` ブロックのコメント参照）。

### 1.1 停止したときに何が起きるか（`blocker-snapshot` との違い）

| | `blocker-snapshot` | `project-status-sync`（本手順） |
|---|---|---|
| 止まると | snapshot が古くなり、到達不能環境の gate が **fail-close**（着手できなくなる） | ボードの `Status` が古いまま残る。**gate の判定は変わらない** |
| 緊急度 | 高（`/issue-pipeline` がリモート環境で使えなくなる） | 中（ボード表示と gate の食い違いが復活する。Issue #460 が解こうとした問題そのものが戻る） |
| 保険経路で足りるか | 足りない（staleness 上限10分 < 実測74〜104分） | 部分的に足りる（鮮度上限60分・書き込みは行われる。ただし追従の遅れは残る） |

つまり本ワークフローの外部 cron が止まっても危険側には倒れない。それでも復旧が要るのは、
**ボードが gate に追従しない状態は Issue #460 以前へ戻ることを意味する**ため。

## 2. cron-job.org のジョブ設定

Console（<https://cron-job.org/en/>）でログイン後、次の内容で**新しいジョブを作成する**
（`blocker-snapshot` 用のジョブを編集・複製して使い回さない＝§2.1）。

| 設定項目 | 値 |
|---|---|
| Title | `project-status-sync dispatch (review-system)` |
| URL | `https://api.github.com/repos/hiratashinnya/review-system/actions/workflows/project-status-sync.yml/dispatches` |
| Request method | `POST` |
| Schedule | 毎時 `0,20,40` 分・毎時・毎日・毎月・毎曜日（＝20分間隔）／timezone `UTC` |
| Headers | `Accept: application/vnd.github+json`<br>`Authorization: Bearer <FINE_GRAINED_PAT>`<br>`X-GitHub-Api-Version: 2026-03-10`<br>`Content-Type: application/json` |
| Body | `{"ref":"main","inputs":{"apply":"true"}}` |
| 成功判定 | HTTP `2xx`（[GitHub REST API docs: Create a workflow dispatch event](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event) によれば成功時は `204 No Content`。実装エージェントは外部 API を実際に叩いて確認できないため未実測——`2xx` 全体を成功とみなす設定にしておけば具体的な code の違いは吸収される） |
| Save responses | 有効（失敗時の切り分け用。`401`（PAT 失効）・`422`（`inputs` の値が不正）をここで見る） |

`<FINE_GRAINED_PAT>` はプレースホルダであり、実際の値は §3 の PAT に置き換える。
この値を本ドキュメント・commit・PR・Issue コメントのいずれにも平文で残さないこと。

### 2.1 `blocker-snapshot` 用ジョブの設定を流用してはいけない

`docs/methods/blocker-snapshot-external-cron-ops.md` §2 のジョブは body が `{"ref":"main"}` で、
**`inputs` を含まない**。この body を本ワークフローに向けると、`workflow_dispatch` の入力 `apply` は
ワークフロー定義の `default: false` に落ちる。ワークフローは `github.event_name` で `--apply` の
付与を決めており、`workflow_dispatch` 経路では入力が `true` のときだけ書き込むので、
**常用運転が永久に dry-run になる**——`Status` が同期されないまま run は成功し CI は緑、という
静かな未達になる（Issue #470 が `schedule` 経路で塞いだのと同じ形が、外部 cron 経路へ移動する）。

`workflow_dispatch` を無条件で apply にすれば防げるように見えるが、そうはしない。外部 cron の
dispatch と人手の dispatch は `github.event_name` では原理的に区別できず、無条件 apply は
PR #465 の finding F-460-01 で回復した**手動 dry-run 経路**を失わせる。したがって
**起動する側（本ジョブ）が `inputs` を明示する**のが唯一の解である。

`inputs` の値は **文字列 `"true"`** で渡す（`workflow_dispatch` REST API の `inputs` は
値を文字列で受け取る）。ワークフロー側は `[ "${APPLY:-false}" = "true" ]` で比較するため、
文字列 `"true"` がそのまま期待どおりに働く。

### 2.2 API で作る場合の等価な設定（参考・Console 操作の代替）

```bash
curl -X PUT \
     -H 'Content-Type: application/json' \
     -H 'Authorization: Bearer <CRONJOB_ORG_API_KEY>' \
     -d '{
       "job": {
         "title": "project-status-sync dispatch (review-system)",
         "url": "https://api.github.com/repos/hiratashinnya/review-system/actions/workflows/project-status-sync.yml/dispatches",
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
           "body": "{\"ref\":\"main\",\"inputs\":{\"apply\":\"true\"}}"
         },
         "schedule": {
           "timezone": "UTC",
           "expiresAt": 0,
           "hours": [-1],
           "mdays": [-1],
           "minutes": [0,20,40],
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

## 3. PAT（`blocker-snapshot` 用の再利用を第一候補とする・未検証）

本ジョブが必要とするのは `POST .../actions/workflows/<file>/dispatches` を叩く権限だけであり、
これは `docs/methods/blocker-snapshot-external-cron-ops.md` §3 で発行済みの fine-grained PAT
（Resource owner `hiratashinnya` / Repository access: `review-system` のみ /
Permissions: **Actions: Read and write** のみ）と同じ条件で足りる**見込み**である。

> **この再利用可否は未検証である。** 実装エージェントは外部 API を実際に叩けないため、
> 「同一リポジトリの別ワークフローに対する `dispatches` が既存 PAT で 2xx を返すこと」を
> 実測していない。オーナーが §4.1 の疎通確認で最初の dispatch が成功することを確認するまでは、
> 再利用できたものとして扱わないこと。`403`/`404` が返る場合は §3.1 の手順で本ジョブ専用の
> PAT を発行して切り分ける。

再利用する場合の運用上の含意:

- **失効の影響範囲が広がる**。PAT が期限切れになると `blocker-snapshot`（gate の生命線）と
  本ワークフローの両方が同時に止まる。ただしどちらも安全側の劣化である（前者は gate が
  fail-close、後者はボード表示が古くなるだけ）。
- **rotation 手順は1本で済む**。`blocker-snapshot` 側の §「PAT 更新（rotation）手順」で
  新 PAT に差し替えるとき、**cron-job.org の2ジョブ両方の `Authorization` header を
  差し替える**こと（片方だけ更新すると、更新し忘れた側が静かに `401` で止まる）。

### 3.1 専用 PAT を発行する場合

GitHub の Settings → Developer settings → Personal access tokens → Fine-grained tokens で、
`blocker-snapshot` 用と同じ条件（Resource owner `hiratashinnya` / Repository access:
**Only select repositories → `review-system`** / Permissions: **Actions: Read and write** のみ /
Expiration: 有効期限を設定する）で発行し、§2 の `Authorization` header に貼り付ける。
値をリポジトリ内のどのファイル・コミット・Issue/PR コメントにも平文で残さないこと。

### 3.2 PAT 期限切れ時の挙動（安全側の劣化）

1. cron-job.org のジョブが `401 Unauthorized` を受け取る（実行履歴に記録される）。
2. `workflow_dispatch` による起動が止まり、純正 `schedule`（実測 74〜104 分間隔）だけが残る。
3. ボードの `Status` が gate の判定に追従するまでの時間が延びる。
   **`Status` が誤った値に書き換わることはない**——`schedule` 経路も `--apply` を付けて同じ
   遷移表で動くため、遅くなるだけで内容は正しい。
4. `blocker-snapshot` 自体が同時に止まっている場合は、`snapshot.json` の鮮度上限（60分）を
   超えた時点で本ワークフローが `SNAPSHOT_STALE` で abort し、**1件も書かない**
   （`project_status_sync/README.md`「書かない・止める条件」）。

## 4. 疎通確認の方法

### 4.1 GitHub 側の起動実績を見る

```
gh run list --workflow=project-status-sync.yml --limit 10 --json event,createdAt,conclusion
```

`event=workflow_dispatch` の行が20分間隔前後で並んでいれば外部 cron が機能している。
`event=schedule` の行しかない場合は外部 cron が止まっている（PAT 失効・cron-job.org 側の障害等）。

本ワークフローは `concurrency.cancel-in-progress: false` なので、`blocker-snapshot` と違って
キュー待ちが cancel の連鎖を起こすことはない（`docs/methods/blocker-snapshot-external-cron-ops.md`
§4.1 の `cancelled` 除外の注意は本ワークフローには当てはまらない）。

### 4.2 dispatch が dry-run に落ちていないことを確認する（**本手順に固有・最重要**）

`event=workflow_dispatch` の run が並んでいても、body に `inputs.apply` が無ければ
**すべて dry-run**であり、ボードは一切更新されない。run summary で実際に書き込んだかを見る。

```
gh run view <RUN_ID> --log
```

run summary（`$GITHUB_STEP_SUMMARY`）は `python3 -m project_status_sync sync` の出力そのもので、
dry-run のときは「計画」だけが並び `applied` が増えない。**「変更計画に行があるのに
Project の `Status` が変わらない」状態が続いていたら、まず §2 の body を疑うこと。**

補助的な確認として、publish 先の孤立ブランチのレポートも見られる。

```
git fetch origin project-status-sync-report
git show origin/project-status-sync-report:report.json
```

`project-status-sync-report/v1` の JSON に `applied[]` が入っていれば実際に書き込まれている。

### 4.3 cron-job.org 側の実行履歴を見る

cron-job.org の REST API `GET /jobs/<jobId>/history`（Console からも同等の履歴が閲覧できる）で、
実行間隔（jitter）とレスポンスコードを確認する。§2 で `Save responses: 有効` にしていれば、
`401`（PAT 失効）や `422`（`inputs` の値が不正）もここで気づける。

### 4.4 確認の頻度と担当

- **頻度**: リポジトリオーナーが、少なくとも週1回、§4.1 と §4.2 を確認する。
  `blocker-snapshot` 側の週次確認（`docs/methods/blocker-snapshot-external-cron-ops.md`
  §「失効検知の頻度と担当」）と同じタイミングでまとめて行えばよい。
- **担当**: 冒頭「実施者」のとおり、cron-job.org・GitHub PAT はいずれも本リポジトリ外の
  認証情報であり実装エージェントは扱えないため、**リポジトリオーナーが実施する**。

## 5. 信頼モデル：この PAT はボードを直接書き換えられない

Project へ書き込むのは常に Actions 上の workflow であり、その認証は repository secret
`PROJECT_SYNC_TOKEN`（classic PAT・scope は `project` のみ）である。外部 cron が持つ
fine-grained PAT（`Actions: Read and write`）は **「同期を始めさせる引き金」だけ**を持つ。

| PAT でできること | 影響 |
|---|---|
| ワークフローを何度も起動する | 同期が余計に走るだけ。遷移表は変わらず、差分が無ければ書き込み API も呼ばれない |
| ワークフローを無効化する／実行をキャンセルする | ボードが古くなる（gate の判定には影響しない） |
| `inputs.apply=true` を付けて起動する | 確認済みの遷移表どおりの書き込みが走るだけ。`Done` への書き込み・オーナー専権フィールド（`Horizon`/`Priority`/`Review date`/`Workstream`/`Harness`）・closed Issue はツール側で機械的に拒否される（`project_status_sync/README.md`「禁止事項（機械的に守る）」） |
| **書き込む内容そのものを指定する** | **できない**。書き込む内容は `snapshot.json` と遷移表から機械的に決まり、外部からの入力は `apply` の真偽だけ |

## 6. 課金（無課金で完結）

- cron-job.org: 分単位のスケジュールを含め無料（`blocker-snapshot` 用ジョブと同アカウント）。
- GitHub Actions: 本 repository は public のため実行時間の課金は発生しない。
- GitHub API 消費: 20分間隔で `POST .../dispatches` を叩くと 72 requests/日。`blocker-snapshot`
  用の 288 requests/日 と合算しても、fine-grained PAT のレート上限 5,000 requests/時 に十分収まる。

課金が発生する構成に切り替える場合は、実装前にオーナーの明示的な認可が必要
（`CLAUDE.md`「CI/外部サービス連携のコスト方針」）。本手順はその必要がない無課金構成である。

## 7. 未確認事項（cron-job.org 設定後に実測すること）

実装エージェントは外部サービスを叩けないため、次はオーナーが設定後に実測して確認する。

- **`blocker-snapshot` 用 fine-grained PAT を本ジョブで再利用できること**（§3・最優先）。
  最初の dispatch が `2xx` を返すかで判定する。`403`/`404` なら §3.1 の専用 PAT へ切り替える。
- `inputs` に文字列 `"true"` を渡した dispatch が `422` にならず、run で実際に `--apply` が
  付くこと（§4.2 で `applied[]` が増えることを確認する）。
- cron-job.org の実際の起動精度（jitter）と、20分 cadence が保たれること。
- 誤って `inputs` 無しの body で登録した場合に、§4.2 の手順でそれを検出できること
  （運用手順として有効かどうかの確認）。

実測後、Issue #470 のコメントに結果を残すこと。
