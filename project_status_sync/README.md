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

trigger は **`schedule`（`*/20 * * * *`）と `workflow_dispatch` の2つ**。

| trigger | `--apply` | 用途 |
|---|---|---|
| `schedule`（cron・20分間隔） | **常に付く** | 常用運転。ボードを gate の判定に追従させる |
| `workflow_dispatch` | 入力 `apply`（既定 `false`）が `true` のときだけ付く | 手動 dry-run／臨時の手動同期 |

**`--apply` の分岐は `github.event_name`（trigger 名）で行い、`inputs.apply` の値だけでは
判定しない**。`inputs` は `workflow_dispatch` でのみ存在し、`schedule` 発火時は空文字に
なる。空文字は「未定義」ではないので `${APPLY:-false}` のような既定値は効かず、
`inputs.apply` 任せの分岐は **cron 実行を永久に dry-run にする**——Status が同期されない
まま CI だけ緑で回り続ける静かな未達になる（Issue #470）。ワークフロー側の分岐は
`case "$EVENT_NAME" in ... esac` に閉じてあり、`tests/unit/test_project_status_sync.py`
がその区間を抜き出して bash で実行し、trigger ごとの `--apply` 付与を固定している。
未知の trigger が増えた場合は dry-run 側へ倒れる（fail-safe）。

cron 有効化に先立ち、初回の変更計画は human-in-the-loop で確認済み（Issue #470・
オーナー承認 2026-09-03）。Project への書き込みには復元手段が無いため、cron と同時に
入れると初回確認が20分タイマーとの競争になって成立しない——という理由で確認を先行させた
（PR #465 の finding F-460-01）。

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

なお GitHub の `schedule` 配信は cron 式どおりの間隔を保証せず、実測で数十分〜100 分規模の
遅延・欠落が起こる（Issue #363）。これは 60 分という上限を弱めない——読む snapshot の鮮度を
決めるのは `blocker-snapshot` 側の cadence（外部 cron・約5分）であって本ワークフローの
発火間隔ではないため、本ワークフローが遅れて発火しても snapshot は通常どおり新しい。
遅延で劣化するのはボード表示が gate に追いつくまでの時間だけで、gate の判定には影響しない。

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
