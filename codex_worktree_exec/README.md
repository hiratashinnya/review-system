# `codex_worktree_exec` — Codex を自分の worktree で実行者として起動する

Claude Code の工程ロールと `issue-fixer` が、自分の linked worktree で元ロールの権限を維持して
Codex を起動する `codex exec -C <worktree>` の薄いラッパー（#538、#371）。

```
python3 -m codex_worktree_exec --role <自ロール> -C <自分の worktree ルート> --prompt-file <依頼文> --output-file <最終応答> --model <モデル> --reasoning-effort <low|medium|high|xhigh|max> [--timeout-seconds <1〜3600>]
```

契約（検査の順序と識別子・permission profile・設計の暫定決定・既知の限界）は
[`docs/methods/codex-workspace-binding.md`](../docs/methods/codex-workspace-binding.md) を正とする。

## モジュール

| モジュール | 責務 |
|---|---|
| `roles.py` | 著作・read-only・fixer の起動対象ロール。両PFのcommand hookも読む |
| `arguments.py` | 引数の検査と `ExecRequest` の組立て |
| `request.py` | 検査済みの起動要求（データだけ） |
| `nesting_guard.py` | Codex の内側からの再帰起動の拒否 |
| `worktree_binding.py` | `-C` が呼び出し元自身の linked worktree であることの確認 |
| `profile_pin.py` | `.codex/config.toml` が `origin/main` の版と同一であることの確認 |
| `project_trust.py` | main checkout が Codex で trust 済みであることの確認 |
| `prompt_files.py` | 依頼文の読込みと最終応答の書き先の確認 |
| `invocation.py` | `codex exec` の argv と前置き付き依頼文の組立て |
| `launcher.py` | `codex exec` の起動、終了コードの透過、timeout |
| `cli.py` | 検査を順に通して起動する入口 |
| `artifact_binding.py` / `initial_binding.py` | 信頼callerの期待値、committed artifact、初回Issue snapshotの束縛 |
| `committed_artifact.py` / `source_snapshot.py` | commit済み入力とsource snapshotの確認 |
| `adviser_request.py` / `adviser_capture.py` | 相談入力・予算と完全回答・trusted使用量の確認 |

profile の生成・digest 検査・bwrap・台帳連携は持たない。区分は
`.claude/rules/02-decision-process.md`「起票先はプロジェクト区分で決める」の汎用開発ハーネスである。

`issue-fixer` 以外は `--binding-file <信頼callerのJSON>` が必須。入力artifactのbytes digestと
envelopeのinput digestを分け、expected値をartifactからコピーして補完しない。
著作ロールはworkspace編集、調査・レビュー・adviserはread-only profileを使う。
全ロールでnetworkと認証情報を拒否し、commit/pushは呼び出し側Claudeの許可ロールだけが行う。
origin/mainとのprofile pinは維持するため、未merge profileの実起動は拒否される。
新工程のnative dispatchはmanifestでavailableとし、入力・独立review・owner承認を必須にする。
worktree継承は `FBK-20261017-工程別worktreeへ同一branchを継承する` に従って各作者専用worktreeへ
同branch/remote exact OIDをadoptする。前roleのreceipt回収・終了・collect/releaseを確認する。
旧版のowner未決・native unavailableは決定前の履歴。新profileのlive実測は #652 で追跡し、
D1 origin/main pinによる未merge拒否とD5 cwd一致を維持する。拒否を成功dispatchと報告しない。

### adviserの要求・回答契約

主文脈のtrusted dispatcherは既存phase承認で確定した相談元のcaller_role/run_id/issue/
phase/work_unit/target_key/snapshot_oidとinput_refs（pathとSHA-256）をAdviceRequestへ入れる。
承認済みwork unit自体の判定は既存phase承認境界が担い、相談実行者にcontextを選び直させない。
作者のphaseはissue_envelope.schema.CONTRACTSと一致させる。implementer/fixerはimplementation、
plan-reviewerはverification_design/solution_planning、pr-reviewerは審査対象の
 test_design/solution_planningまたはimplementationを使う。
調査・1a・1bのように計画のwork unitがまだない段階でも相談できる。このときwork_unitには
trusted dispatcherが当該工程内で一意に固定した非空の作業単位（例: investigation-main）を入れる。
2a/2b/是正では既存承認から得たwork unitをそのまま使う。

要求にはmax_calls/calls_used、max_tokens/tokens_used/reserve_tokens、
max_cost_microusd/cost_used_microusd/reserve_cost_microusd、
max_seconds/seconds_used/reserve_secondsをすべて入れる。回数/token/費用は非負整数、
秒は有限の非負数で、各予約は正数とする。残予算を超える予約と呼出し前の上限到達は拒否する。
回答は要求全体のrequest_digestと全origin fieldを明示して返し、captureはtrusted callerが
保持した要求と両方を比較する。同じrun/targetでも別phase/work unitの回答は拒否する。
モデル選択は既存model_policy/Bloom正本に従い、相談用のresolverや別の永続台帳は作らない。

trusted meterはstatus/tokens/cost_microusd/elapsed_secondsを返す。elapsed_secondsは
実行者の回答値や壁時計の差ではなくtrusted executorが単調時計で測った経過秒である。
不明値を0へ補完せず、欠落/非有限/負値/bool/任意のclock欄は拒否する。
実測が予約を超えた場合、または累計時間/token/費用が上限に到達した場合は成功にしない。
最終許可回の成功はcalls_usedへ加算し、次回要求は回数上限で拒否する。
成功captureはorigin、要求digest、予算、累計回数/時間/token/費用、trusted実測を返す。
失敗・部分出力・予算到達はAdviceCaptureError.recordへ同じorigin/予算/受領実測を保持し、
主文脈が既存runの担当成果物から追跡する。実測が欠落した失敗も欠落のまま残す。
採否/理由/検証はpendingから元担当が記録する。助言は必須レビュー、STOP、karte escalate、
権限拒否、owner承認を代替しない。live実行の確認はmerge後の#652で行い、ここでは未実測である。

### 2a/2bの単一work unit入力

`test-writer` のCP bindingは `expected.work_unit` がCP内に一つ存在することを要求する。2aの `pr-reviewer` はTestDesignの必須work_unitと同じcaller期待値を渡す。TestDesignは `input_refs=[承認CPのID]` と `input_digest=そのCPのSHA-256` を保持する。2bの `issue-implementer` とPR対象の `pr-reviewer` は既存CP bindingに加え `expected.test_design={artifact, artifact_digest}` で消費TDを指定する。共通 `work_unit_binding` がcommit済みTDのCP/digest/unit/run/Issue/target/snapshotを照合する。この参照は独立review/owner承認の代替ではなく、nativeの2a review receiptが指す参照と完全一致しなければならない。
