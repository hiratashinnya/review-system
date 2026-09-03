# project_status_sync

GitHub Project「review-system Development」の `Status` を、`blocker-snapshot` ブランチに
publish 済みの `snapshot.json` から同期する CLI（Issue #460）。標準ライブラリのみ。

`Blocked` を設定する built-in workflow は存在せず、`In progress` に入る契機も無いため、
「gate は着手を fail-close で拒否するのにボードは `Ready` のまま」という食い違いが常時
起こりうる。本ツールはその2区間のうち `Blocked` の設定/解除を機械化する
（`In progress` は `/issue-pipeline` 主文脈が着手宣言点で設定する＝`.ai/skills/issue-pipeline/SKILL.md` ②-a）。

## 使い方

```
python3 -m project_status_sync sync \
  --repository OWNER/REPO \
  --project-id PVT_... \
  [--project-number 1] \
  --snapshot path/to/snapshot.json \
  --report path/to/report.json \
  [--max-age-seconds 3600] \
  [--apply]
```

- **既定は dry-run**。書き込みは `--apply` を明示したときだけ（`dsv2 reverse` と同じ流儀）。
  誤実行でボード全体が書き換わると復元手段が無いため。
- stdout＝`$GITHUB_STEP_SUMMARY` 用 markdown、stderr＝1行要約、`--report`＝`project-status-sync-report/v1` の JSON。
- 認証は環境変数 `PROJECT_SYNC_TOKEN`（classic PAT・scope は `project` のみ）。
  Actions の `GITHUB_TOKEN` へは意図的に fallback しない——fallback すると
  「権限不足」と「secret 未設定」を切り分けられなくなる。

### GitHub Actions からの実行（`.github/workflows/project-status-sync.yml`）

現在の trigger は **`workflow_dispatch` のみ**で、`--apply` は入力 `apply`（既定 `false`）が
`true` のときだけ付く。**`schedule`（cron）は本 PR ではあえて入れていない**
（PR #465 の finding F-460-01・オーナー確定 2026-09-03）。

理由：`inputs.apply` を足すだけでは merge から20分以内に cron が `--apply` で発火し、
「まず dry-run で変更計画を確認する」という初回確認が20分タイマーとの競争になって実質的に
成立しない。Project への書き込みには復元手段が無いため、確認が先に成立するようにする。

運用の順序：

1. merge 後、オーナーが `workflow_dispatch` を `apply: false`（既定）で実行する。
2. `$GITHUB_STEP_SUMMARY` に出る変更計画を確認する。
3. 問題なければ **後続 PR で `on: schedule`（20分間隔）を有効化**して常用に入る。
   その PR では、`schedule` 発火時に `inputs.apply` が空文字になる（`inputs` は
   `workflow_dispatch` でのみ存在する）ため、schedule 時に `--apply` を付けるかどうかを
   明示的に決めること。現状のワークフローは既定を dry-run 側に倒してある。

### exit code

| code | 意味 |
|---|---|
| 0 | 正常（変更の有無を問わない・警告なし） |
| 20 | 中断または警告あり。**`report` は書けている**ので、呼出側は publish してから赤くする |
| 2 | 引数不正・report 書込不能 |

## 判定仕様

ブロッカー判定は再実装せず `blocker_gate` をそのまま呼ぶ（`planner._findings`）。
gate と board が別の答えを出すこと自体が本 Issue の解こうとしている問題なので、
同じ意味の実装を2つ持たない。

1. `blocker_gate.snapshot.project_issue_snapshot` で1 Issue 分を射影
2. `blocker_gate.evaluator.validate_graph`
3. `evaluate_dependencies` … `blocked_by` を**推移的に**辿り、**closed のブロッカーで打ち切る**
   （`A --blocked_by--> B(closed) --blocked_by--> C(open)` の A はブロックされない）
4. `evaluate_closure_invariant` … closed の親に open の子孫がいる場合だけ検出する。
   open な親は skip されるため、**親子関係は `Blocked` の判定に使わない**
   （閉じ方の不変条件であって、着手を妨げる依存ではない）

waiver（`blocker_gate.waiver`）は適用しない。ボードは「依存グラフが実際にどうなって
いるか」を映す方が誤解が少なく、waiver 適用の可否は Issue #460 のスコープ外。

## 遷移表

| 現在の Status | ブロッカーあり | ブロッカーなし |
|---|---|---|
| `Inbox` / `Ready` | → `Blocked` | 触らない |
| `Blocked` | 触らない | → `Ready` |
| `In progress` / `In review` | **触らない**＋警告＋CI赤 | 触らない |
| `Done` / closed Issue | 対象外 | 対象外 |

`In progress` / `In review` を書き込み対象から外すことで、cron が進行中の作業を巻き戻す
競合が検査ではなく構造で消える。`Blocked` に入るのが `{Inbox, Ready}` からだけなので、
解除時に `Ready` へ戻しても情報を失わない。

## 書かない・止める条件

`report.json` の `skipped[]` は **CI を赤くしない**。`warnings[]` と `abort` は赤くする。

| 区分 | code | 挙動 |
|---|---|---|
| skipped | `NOT_IN_SNAPSHOT` | snapshot（約5分間隔）と本ワークフロー（20分間隔）は周期が違うため構造的に必ず発生する。故障ではないので赤くしない。次回実行で自動収束 |
| skipped | `STATUS_UNSET` | 「未設定」自体が「まだトリアージしていない」という情報でありうる。遷移表に無い遷移を機械が発明しない |
| skipped | `STATUS_UNKNOWN` | 語彙外＝オーナーが意図して追加した状態である可能性が高い。誤って書くと Project には復元手段がないので書かない側に倒す |
| warning | `ACTIVE_ITEM_BLOCKED` | `In progress` / `In review` にブロッカーが付いた。Status は変更せず赤くする |
| warning | `CLOSURE_OPEN_DESCENDANT` | closed の親に open の子孫がある（グラフ不整合）。当該 Issue の Status を書かず赤くする |
| abort | `SNAPSHOT_INVALID` | snapshot を読めない／schema 不正 |
| abort | `SNAPSHOT_DEGRADED` | `pages_complete: false` または `errors` 非空 |
| abort | `SNAPSHOT_STALE` | `generated_at` が 60 分より古い（既定） |
| abort | `GRAPH_UNREADABLE` | evaluator がグラフを評価できない |
| abort | `ISSUE_STATE_UNKNOWN` | 依存グラフに状態不明の Issue がある |
| abort | `PROJECT_UNREADABLE` | Project / Status field を読めない・token 未設定 |
| abort | `APPLY_FAILED` | 書き込み中に失敗（成功済みの分は `applied[]` に残る） |

`abort` のときは **1件も書かない**（Project API を叩く前に snapshot 側の abort を確定させる
ので、degraded・鮮度超過は実行順序で保証される）。

### 鮮度上限が 60 分である理由

degraded 判定（`pages_complete` / `errors`）は「壊れた snapshot」しか捕まえられず、
「壊れていないが古い」snapshot は素通りする。gate は staleness 10 分で fail-close するが、
本ワークフローは20分周期のため同じ値だと通常運転で自分を弾く。60 分なら通常運転では
発火せず、`blocker-snapshot` が実際に停止した異常だけを捕まえられる。

## 禁止事項（機械的に守る）

- **`Done` を書かない**。遷移先は `WRITABLE_TARGETS = {Ready, Blocked}` に閉じており、
  `cli._apply` がそこに無い遷移先を書き込み前に拒否する。`Done` 書き込みは built-in
  workflow `Auto-close issue` により Issue の close と等価であり、自動化に close 権限を
  持たせないため。
- **closed の Issue は対象外**。
- **`Horizon` / `Priority` / `Review date` / `Workstream` / `Harness` に触らない**
  （`model.OWNER_ONLY_FIELDS`）。read query も mutation も `Status` field 1つしか扱わない。
- **差分がない項目に書き込み API を呼ばない**（計画に載るのは実際の遷移だけ）。

## Status field id を live 解決する理由

option id を定数で持つと、(a) field を作り直したときに静かに別 field を指しうる、
(b) 語彙外 option（`STATUS_UNKNOWN`）の検出には option 一覧の取得が必要で、取得するなら
id も同時に得られる——ので、`field(name: "Status")` を毎回引いて id を解決する。
`--project-number` を渡すと Project の number を照合し、別 Project への誤書き込みを防ぐ。

## 起票先

`.claude/rules/02-decision-process.md`「起票先はプロジェクト区分で決める」の
**どちらのシステムにも含有されない汎用開発ハーネス**（CI 定義・`blocker_gate` 周辺の
運用ツールと同区分）。指摘・改善は Issue で起票する（ノード起票の対象外）。
