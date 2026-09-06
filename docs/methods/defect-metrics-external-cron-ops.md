# defect-metrics: 外部 cron（cron-job.org）運用手順

- 対象: Issue #488（本ツールの実装）、Issue #489（外部 cron の実設定と初回到達の実測確認）、
  Issue #370（親・欠陥分類の供給と再計測）、Issue #368（基線の定義）
- 関連正本: `.github/workflows/defect-metrics.yml`、`defect_metrics/README.md`
- 前例: `docs/methods/blocker-snapshot-external-cron-ops.md`（同じ方式・同じ粒度）
- 実施者: 本ドキュメントの手順（cron-job.org のジョブ登録・PAT 発行・疎通確認）は
  **リポジトリオーナーが Console 上で手動実施する**。実装エージェント（`issue-implementer` 等）は
  実施しない・実施できない（GitHub 外のサービスの認証情報を扱うため）。

## 1. 背景（なぜこの手順が必要か）

`.github/workflows/defect-metrics.yml` は、欠陥混入率の指標（`defect_metrics/README.md` §2）を
算出し、孤立ブランチ `defect-metrics` の `report.json` へ publish する。これがないと、
#370 / #368 / #371 が要求する「基線との比較」も「対策投入後の回帰検知」も、誰も見ていない
ために成立しない。

Issue #363 の実測により、GitHub の `schedule:` は cron 式どおりの間隔での発火を保証しない
（`*/5` の指定に対し実測 74〜104 分間隔）ことが判明している。本ワークフローは**週次**なので
schedule の遅延そのものは致命的ではないが、次の2点から外部 cron を主たる起動元とする。

- public repository の scheduled workflow は **60 日間の無活動で自動停止する**。週次の
  schedule は「無活動」ではないので直ちには止まらないが、GitHub 側の都合で欠落した週が
  静かに積み上がる経路が残る。`workflow_dispatch` 起動はこの 60 日ルールの対象外である。
- 起動時刻が読めないと、`report.json` の `generated_at` を見ても「まだ来ていない」のか
  「壊れている」のかを区別できない。外部 cron なら期待時刻が確定するので、鮮度で異常に
  気づける。

`schedule:` は外部 cron が止まったときの保険として残す。

## 2. cron-job.org のジョブ設定

Console（<https://cron-job.org/en/>）でログイン後、次の内容でジョブを作成する。

| 設定項目 | 値 |
|---|---|
| Title | `defect-metrics dispatch (review-system)` |
| URL | `https://api.github.com/repos/hiratashinnya/review-system/actions/workflows/defect-metrics.yml/dispatches` |
| Request method | `POST` |
| Schedule | 毎週月曜 `03:30`（時 `3`・分 `30`・曜日 `Monday`・毎月・毎日は曜日で絞る）／timezone `UTC` |
| Headers | `Accept: application/vnd.github+json`<br>`Authorization: Bearer <FINE_GRAINED_PAT>`<br>`X-GitHub-Api-Version: 2026-03-10`<br>`Content-Type: application/json` |
| Body | `{"ref":"main"}` |
| 成功判定 | HTTP `2xx`（[GitHub REST API docs: Create a workflow dispatch event](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event) によれば成功時は `204 No Content`。`2xx` 全体を成功とみなす設定にしておけば具体的な code の違いは吸収される） |
| Save responses | 有効（失敗時の切り分け用。上記 endpoint は成功時 body を返さず、失敗時も GitHub の標準エラー JSON を返す） |

`<FINE_GRAINED_PAT>` はプレースホルダであり、実際の値は §3 で発行する PAT に置き換える。
この値を本ドキュメント・commit・PR・Issue コメントのいずれにも平文で残さないこと。

> **`schedule:` との時刻をずらしてある。** ワークフロー側の保険 schedule は毎週月曜 `03:17 UTC`、
> 外部 cron は `03:30 UTC` である。同時刻にすると `concurrency.group: defect-metrics` により
> 片方が待たされ、どちらが実際に publish したのか実行履歴から読み取りにくくなる。

> **他のワークフローへ本ジョブ設定を流用しないこと。** 上表の Body `{"ref":"main"}` は
> `inputs` を含まない。`workflow_dispatch` の入力で挙動が変わるワークフローにこの body を
> 向けると、入力はワークフロー定義の既定値に落ちる（実例＝`project-status-sync.yml` が
> 永久 dry-run になる・Issue #470）。`defect-metrics.yml` は `inputs` を持たないため、
> この body で意図どおりに動く。

### API で作る場合の等価な設定（参考・Console 操作の代替）

```bash
curl -X PUT \
     -H 'Content-Type: application/json' \
     -H 'Authorization: Bearer <CRONJOB_ORG_API_KEY>' \
     -d '{
       "job": {
         "title": "defect-metrics dispatch (review-system)",
         "url": "https://api.github.com/repos/hiratashinnya/review-system/actions/workflows/defect-metrics.yml/dispatches",
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
           "hours": [3],
           "mdays": [-1],
           "minutes": [30],
           "months": [-1],
           "wdays": [1]
         }
       }
     }' \
     https://api.cron-job.org/jobs
```

`requestMethod: 1` は cron-job.org REST API の `RequestMethod` enum で `POST` を表す
（`0`=GET / `1`=POST / `2`=OPTIONS / `3`=HEAD / `4`=PUT / `5`=DELETE / `6`=TRACE / `7`=CONNECT / `8`=PATCH）。
`wdays: [1]` は月曜（`0`=日曜）。

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
| Expiration | 有効期限を設定する（無期限にしない） | 期限切れ時は cron-job.org 側で `401` になる。これは計測を止める方向にしか働かない（§5） |

**`blocker-snapshot` 用の PAT を流用してもよい**（必要権限が同一の `Actions: Read and write`
であり、同一リポジトリに閉じているため）。ただし流用した場合、その PAT の失効は
`blocker-snapshot` と `defect-metrics` の**両方**を同時に止める。切り分けを容易にしたい場合は
別々に発行する。どちらにするかはオーナーの判断であり、本ドキュメントは推奨を置かない。

発行した値はそのまま cron-job.org のジョブ設定（§2 の `Authorization` header）に貼り付ける。
リポジトリ内のどのファイル・コミット・Issue/PR コメントにも平文で残さないこと。

### PAT 期限切れ時の挙動（意図した安全側の劣化）

1. cron-job.org のジョブが `401 Unauthorized` を受け取る（cron-job.org 側の実行履歴に記録される）。
2. `workflow_dispatch` による起動が止まる。`schedule`（毎週月曜 03:17 UTC・遅延あり）だけが残る。
3. `report.json` の `generated_at` が古くなる。
4. レポートを読む側（#461 の報告経路など）は「鮮度が落ちた」ことを検知できる。**古い数字を
   最新として読む方向には倒れない**——`generated_at` が常にレポートに入っているため。

### PAT 更新（rotation）手順

1. §3 の表と同じ条件で新しい PAT を発行する。
2. cron-job.org の Console → 対象ジョブ（`defect-metrics dispatch (review-system)`）→
   Headers の `Authorization: Bearer <FINE_GRAINED_PAT>` を新しい値に差し替えて保存する。
3. §4 の疎通確認を行い、次回 dispatch が成功しレポートが更新されることを確認する。
4. 旧 PAT を GitHub の Settings → Developer settings → Personal access tokens で失効（revoke）する。

失効検知の頻度と担当:

- **頻度**: リポジトリオーナーが、少なくとも月1回、§4.1 の `gh run list` を実行して
  `event=workflow_dispatch` の行が週次で並んでいることを確認する。
- **担当**: 冒頭「実施者」のとおり、cron-job.org・GitHub PAT はいずれも本リポジトリ外の
  認証情報であり実装エージェントは扱えないため、**リポジトリオーナーが実施する**。
  発行時に設定した `Expiration` の日付をオーナー自身が追跡する（リポジトリ内に自動
  リマインダーの仕組みは無い）。

## 4. 疎通確認の方法

### 4.1 GitHub 側の起動実績を見る

```
gh run list --workflow=defect-metrics.yml --limit 10 --json event,createdAt,conclusion
```

`event=workflow_dispatch` の行が週次で並んでいれば外部 cron が機能している。
`event=schedule` の行しかない場合は外部 cron が止まっている（PAT 失効・cron-job.org 側の障害等）。

`conclusion` の読み方は次のとおり（`.github/workflows/defect-metrics.yml`）。

| `conclusion` | 意味 |
|---|---|
| `success` | レポートを publish し、基線も再現できた。**閾値超過（`threshold.anomaly = true`）でも `success` になる**——閾値超過は generator の失敗ではなく計測結果であり、`::warning` で可視化するだけで job は落とさない |
| `failure` | 次の3種類がある。①レポート生成そのものの失敗（`gh` の取得失敗・出力スキーマ変更・取得件数が `--limit` に達した打ち切り）＝**publish されていない**。②**記録済み基線の再現不能**（`verify-baseline` が exit 21）＝レポートは publish された上で、その後の step が `::error` ＋ `exit 1` で job を赤くしている。③`verify-baseline` step 自体が動かなかった（取得エラー等）＝レポートは publish されており、基線の照合結果は `report.json` の `baseline_verification` を読む |

3者の区別は、失敗した step 名（`Compute the defect-rate report` か
`Fail the job when the recorded baseline could not be reproduced` か）と、`::error`
annotation の文面で付く。`defect-metrics` ブランチの `report.json` が更新されているのは
②③だけである。②の詳細は同じ `report.json` の `baseline_verification.mismatches` に
永続化されている（§4.2）。

②を `::warning` に留めない理由は、GitHub が run failure では通知する一方 `::warning`
annotation では通知しないためである。基線が再現しなくなるのは「指標定義を変えた」か
「過去の Issue/PR 本文を編集した」かのどちらかで、いずれも人の判断が要る。緑のまま
放置されると、Issue #488 が解こうとした「散文定義による再現不能」がそのまま再発する。

### 4.2 レポートの鮮度と内容を直接見る

```
git fetch origin defect-metrics
git show origin/defect-metrics:report.json
```

確認する項目:

- `generated_at` が直近の期待実行時刻（毎週月曜 03:30 UTC 前後）と整合するか。
- `schema_version` が `defect_metrics/model.py` の `SCHEMA_VERSION` と一致するか
  （不一致なら読取側のパースを更新する必要がある）。
- `threshold.anomaly` が `true` なら `threshold.alerts` に理由が入っている。
  `false` のときは何も報告しない（`alerts` は空配列）。
- `threshold.skipped` が空でないときは「異常なし」ではなく「判定できなかった」である
  （分母0・直近4週にデータ無し）。正常と読み替えないこと。
- `baseline_verification.reproduced` が `true` か。`false` のときは
  `baseline_verification.mismatches` に「どの値がいくつからいくつへ動いたか」が入っており、
  同じ run は `conclusion = failure` になっている（§4.1）。**この場合、その run の
  レポート自体は publish されているが、`threshold` の基線比較（定数 0.68）は
  「記録済み基線とは別定義の値」との比較になっている**ため、数字を額面どおりに読まないこと。
- `trailing_4_weeks.aggregation.method` が `pooled` であること。直近4週の比は
  **28 日をひとまとめにしたプールド比**であり、週次比4本の平均ではない
  （Issue #488 本文の「直近4週平均」という文言との差異。根拠＝`defect_metrics/README.md` §3）。

### 4.3 cron-job.org 側の実行履歴を見る

cron-job.org の REST API `GET /jobs/<jobId>/history`（Console からも同等の履歴が閲覧できる）で、
実行時刻とレスポンスコードを確認する。§2 で `Save responses: 有効` にしていれば、`401`
（PAT 失効）等の失敗もここで気づける。

### 4.4 手動で1回だけ動かす（初回確認）

```
gh workflow run defect-metrics.yml --ref main
gh run list --workflow=defect-metrics.yml --limit 1
```

外部 cron を設定する前に、この手順でワークフロー自体が通ることを確認しておくとよい。

## 5. 信頼モデル：この PAT はレポートの内容を偽造できない

`docs/methods/blocker-snapshot-external-cron-ops.md` §5 と同じ構造である。**PAT が持つのは
「生成を始めさせる引き金」だけ**であり、レポートの内容そのものを生成するのは常に Actions 上の
ワークフロー（GitHub の `GITHUB_TOKEN` で `gh` から取得）である。

| PAT でできること | 影響 |
|---|---|
| ワークフローを何度も起動する | レポートが余計に更新されるだけ。数字は同じ入力から決定的に決まる |
| ワークフローを無効化する／実行をキャンセルする | レポートが古くなる → `generated_at` の鮮度で気づける |
| **レポートの内容を書き換える** | **できない**。`Actions: Read and write` permission は `defect-metrics` ブランチへの `git push` 権限を含まない（リポジトリ内容への書き込みは `Contents` permission の管轄） |

## 6. 課金（無課金で完結）

`.claude/rules/03-operational.md`「CI/外部サービス連携のコスト方針」に従い、全経路が無課金である
ことを確認した上でこの構成を選んでいる。

- **GitHub Actions**: 本 repository は **public** のため実行時間の課金は発生しない（public
  リポジトリには無料枠の上限自体が存在せず、課金は private リポジトリが無料枠を超えた分に
  だけ適用される）。
- **GitHub API 消費（Actions 側・`GITHUB_TOKEN`）**: 1 実行あたり `gh issue list` /
  `gh pr list` を report step と `verify-baseline` step で1回ずつ、計4コマンド実行する。
  `gh` は 100 件/ページでページングするため、Issue 246 件・merged PR 228 件（2026-09-06
  時点）ではそれぞれ **3 ページ＝約 6 リクエスト**、2 step 合計で **約 12 リクエスト/実行**
  になる。`GITHUB_TOKEN` の枠は **1,000 requests/h** であり、週1回・約 12 リクエストは
  無視できる（件数の増加に比例して増えるが、週1回である限り枠に対して桁が違う）。
  この数値は `.github/workflows/defect-metrics.yml` 冒頭のコメントと一致させること。
- **GitHub API 消費（外部 cron 側・fine-grained PAT）**: `POST .../dispatches` は週1回＝
  **約 4 requests/月**。fine-grained PAT の枠は `GITHUB_TOKEN` とは別建ての
  **5,000 requests/時** であり、十分収まる（前例＝`docs/methods/blocker-snapshot-external-cron-ops.md`
  §6 が同じ 5,000 requests/時 を PAT の枠として記載している。**5,000 は PAT の枠であって
  `GITHUB_TOKEN` の枠ではない**）。
- **cron-job.org**: 公式トップページに「from minute-by-minute to once in a year. Absolutely
  free.」と明記。週次はもちろん無料枠内である。

課金が発生する構成に切り替える場合は、実装前にオーナーの明示的な認可が必要
（同節「課金必須の場合は選択肢＋推奨を添えて認可を仰ぐ」）。本手順はその必要がない無課金構成である。

## 7. 未確認事項（cron-job.org 設定後に実測すること＝Issue #489）

次はオーナーが cron-job.org を実際に設定した後でなければ検証できない。実装エージェントは
この検証を代行できない（Issue #488 の Out of scope・実装と live 実測を同じ Issue に載せない）。

- 外部 cron からの `workflow_dispatch` が実際に `2xx` を返し、ワークフローが起動すること。
- 孤立ブランチ `defect-metrics` が実際に作成され、`report.json` が `git fetch` で読めること。
- `generated_at` が期待実行時刻と整合し、週次で更新され続けること。
- `verify-baseline` step が live データに対して緑であり続けること（2026-09-06 時点の実測では
  22 PR / 41 Issue / 1.86 / 派生 15 / 0.68 を再現済み＝`defect_metrics/README.md` §6）。
- 報告経路（#461）へレポートを源として追加する際の読み取り可否。
