# Codex supervisor 方式の退役記録（Issue #538 PR-A）

**これは規範ではない。** Issue #452 が導入し、Issue #538 の PR-A で退役した Codex repo supervisor 方式について、
退役時点まで現行文書・契約・設定に書かれていた内容を移設して保全する
（`.claude/rules/01-principles.md`「PR8「消さない」の適用範囲」区分1）。
現行の状態は [`docs/methods/codex-workspace-binding.md`](../../docs/methods/codex-workspace-binding.md) を正とする。
本書が保全するのは退役した supervisor 方式の手順・契約であり、それらは**現在は有効でない**。
ただし移設本文には、退役の前後で変わらず現在も有効な契約の記述も含まれる
（Codex の `spawn_agent` による既知ロール起動を常時 `ISSUE_START_TRANSPORT_UNAVAILABLE` で拒否すること、
Claude transport の marker／isolation 契約）。何が現在有効かは本書から読み取らず、上記の現行文書を正とする。

## 退役の決定

- 決定の正本は Issue #538（`https://github.com/hiratashinnya/review-system/issues/538`）と、
  `audit/2026-09-21-pipeline-redesign/README.md` の決定 `FBK-20260922-codexを主文脈にせずサブ扱いとする` である。
- オーナーは 2026-09-22 に「Claude Code を主文脈とし、Codex はサブエージェント的な実行者として使う」と決定した。
  supervisor が解いていた問題（Codex の subagent を対象 Issue 専用 worktree へ機械束縛する）は、
  Codex が主文脈であるときにだけ発生する。主文脈を Claude Code にすると前提ごと不要になる。
- supervisor の退役理由として #452 が挙げた制約（custom-agent schema に子ごとの作業ディレクトリ指定がなく、
  親の sandbox と live runtime overrides を継承する）は、Issue #538 起票時点（2026-09-22）でも有効だった。
  退役は「制約が解消したから」ではなく「Codex を主文脈にしないから」である。
- 退役時点で supervisor は P4（実起動検証）を一度も通していない。#452 の P4 implementer/fixer、
  host publish 実運用検証、F-452-31〜36 は未達・未解消の履歴であり、退役によって成功・resolved・PASS へ
  読み替えない（Issue #538「#452からの引き継ぎ（2026-10-09・オーナー承認）」）。

## 退役物

| 種別 | 退役物 |
|---|---|
| module | `issue_start/codex_supervisor.py`・`codex_launch_intent.py`・`codex_launch_control.py`・`codex_supervisor_workspace.py`・`codex_karte_bridge.py` |
| test | `tests/unit/test_codex_supervisor.py`・`test_codex_supervisor_shrink.py`・`test_codex_launch_control.py`・`test_codex_karte_bridge.py`、`tests/unit/test_issue_start_gate.py` の `CodexLaunchIntentTests`、`tests/unit/test_issue_start_cli_assets.py` の `test_codex_launch_manifest_derives_every_non_owner_input`・`test_codex_launch_hook_asset_is_registered_and_executable` |
| hook | `.codex/hooks/codex-launch-intent-gate.sh` と `.codex/hooks.json` の同 PreToolUse 登録 |
| 設定 | `issue_start/managed-entrypoints-v2.json` の top-level block `codex_supervisor_launch` |

`test_codex_karte_bridge.py` にあった `karte.paths.writer_lock` の unsafe lock（symlink・hardlink）拒否テストは、
supervisor ではなく共有 karte の検証である。退役物に含めず、レビュー是正（F-538-01）で
`tests/unit/test_karte_writer_lock.py` として残した。

検証証跡（TD／TR）は `archive/issue-452-codex-supervisor/` へ移し、ログは `tests/logs/TD-issue-start-452-*` に残す。

## 読み方の注意

以下の各節は移設元の文言を尊重して移してある。`「上記」`「下記」「後述」等の相対参照は移設元の文脈を指す。
節見出しは移設先で付与・降格しており、どの文書から来たかを併記している。

## 移設元: `docs/methods/codex-workspace-binding.md`（退役時点の全文）

移設元の表題は「Codex Issue supervisor 実行契約」だった。

### 結論

`collaboration.spawn_agent` 用 workspace binding は退役した。OpenAI公式のcustom agent schemaに
per-subagent作業ディレクトリ指定がなく、subagentは親runtime/workspaceを継承するため、repo側の
prepare/TTL/refreshでは実効workspaceを成立・観測できない。Codex本体の上流改修は利用者側の
恒久策に含めない。

既知の`issue-implementer` / `issue-fixer`を`spawn_agent`で起動しようとした場合、issue-start
gateはpayload、cwd、ledger、GitHub APIを読む前に常時`ISSUE_START_TRANSPORT_UNAVAILABLE`で拒否する。
manifestの`binding_transports.codex`、`issue_start/codex_binding.py`、all-tool binding hookは存在しない。
Claude transportのmarker/isolation契約は変更しない。

### 正規Codex経路

正規経路は`issue_start.codex_supervisor`がIssue専用のdurable worktreeで別Codex CLI processを
起動する経路だけである。

1. 親AIが渡せる値はIssue、role、owner-approved change-plan IDと、fixer時のroundだけである。
2. supervisorはhost private change plan、manifest、構造化Issue/AC（fixerはkarteも）、canonical ledger、
   live Git、role contract、permission profile、実行ファイルから残りを一意に導出する。
3. host control-plane issuerが先に作った`platform=codex-supervisor`のcanonical ledger entryを、同じledger lock transactionで
   immutable intent digestとattemptにより拡張する。第2entryは作らない。secure canonical stateが無ければ
   fail-closeする。
4. private `/tmp`/`/dev`、worktree書込限定、main/common Git/protected assets read-onlyのOS境界で
   `codex --profile issue-supervised --strict-config exec -C <worktree>`を実行する。profileがworkspace-write相当を
   設定し、literal `--sandbox`は併用せずcompatibility検査が`LEGACY_SANDBOX_PRESENT`で拒否する。
5. PIDと`/proc/<pid>/stat` start tokenを記録し、同じprocessのJSONL `thread.started`を1度だけ束縛する。
6. `turn.completed`、exit 0、schema v1 `pre_publish` handoffを全て確認して初めて成功とする。
7. commit/push/PR createはhost publish state machineが段間Git facts CASを検査して実行する。

### Host control-planeの発行

`python3 -m issue_start.codex_launch_control issue`は、owner承認後にproduction change planを発行する
専用入口である。入力はIssue番号、role、change-plan ID、登録済み専用worktreeの絶対path、capture済みの
構造化Issue snapshot、承認者login、fixerの場合だけroundとkarte snapshot、任意のprotected path名に
限定する。repository、branch、OID、task key、handoff、finding ID、content digest、model、runtimeは入力させず、
live Git、manifest、source内容から導出する。承認者と時刻は監査用の運用記録であり、暗号学的な本人証明ではない。

role別の handoff_template はmanifestの正本であり、launch intentはcanonical ledgerの同一role・round・task
entryと照合してからhandoffを導出する。導出済みのrole別相対pathだけをhost promptへexact 1回注入し、
LaunchRequestやsupervisor CLIの自由入力、legacy/unknown template、prompt内の実handoff file candidateは受け付けず
fail-closeする。`branch_name`、`repository`、`expected_oid`もlive Git factsとcanonical ledgerから同じ
host promptへ配送し、親runtimeの4入力（Issue、role、change-plan ID、fixer round）は増やさない。
Issue/karte snapshotをpromptへ埋め込む前に、`tmp/_handoff/`配下の実ファイル候補（canonical pathの再掲、
別role path、attacker pathを含む）と、host authority/prompt reserved fieldに一致するformat placeholderを
検出したらfail-closeする。候補判定はshell実行・展開を行わず、HTML entityをdecodeした本文をpath全体の
deterministic lexerで先頭から末尾まで読み、quote/backtickで分割されたcomponent、POSIX/Windows separator、
root側のdot・重複separatorを正規化してから行う。候補全体の最終semantic path文字がseparatorの場合だけ
directoryとし、途中のquoted separatorをterminal状態として残さない。bareな`tmp/_handoff/`ディレクトリ説明や
reservedでない一般placeholder・コード断片はsnapshotデータとして許可する。snapshotはtemplateへの単一format
passのreplacementなので、replacement内のbraceを再解釈しない。innerはhostが提示した1 pathだけへschema v1 handoffを
書き込む。

issuerはworktreeを作成せず、GitHubにも接続しない。worktree登録とsnapshot captureはcallerであるhost運用の
責務である。capture側はIssueを`github-api`、karteを`karte-cli`で取得・exportした時点のactorとUTC秒を
snapshot schema v2の`capture`へ記録する。issuerはこの記録を形式・source種別・未来時刻でないことまで検証して
change planへそのまま保存するが、GitHub応答やactor本人性の暗号学的証明は行わない。capture actor/time/methodと、
owner approvalのactor/recorded timeは別の事実であり相互に代用しない。capture fieldを持たない旧snapshot v1や
自由文methodはfail-closeする。

発行先はrootからmainまでmanifest読取と同じowner/mode/NSS trust policyで辿り、main配下の`tmp`にも同じpolicy、
`_codex_control`/`sources`/`change-plans`にはcurrent-user 0700を要求する。検査したdirectory FDを発行完了まで保持し、
同じdirfd内で0600 unique tempを`O_EXCL|O_NOFOLLOW`作成、file fsync、hard-linkによるatomic no-clobber publish、
temp unlink、directory fsyncを行う。各段で親entryと保持FDのdevice/inodeを再照合し、rename/symlink swapを検出したら
fail-closeして同じdirfd内の一時物・当該試行の公開物を除去する。world-writable non-stickyまたはforeign principalを
含むgroup-writable ancestorは発行前に拒否する。same-UID非協調processは既存host trust boundary外である。

発行順はcanonical ledger `pending`、private source、ledger `complete`、change planの順で、planを
最後に公開する。途中停止ではruntime loaderがfail-closeし、同じsource・承認者・worktree・plan IDの再実行だけが
同じentryを修復する。retryでは保存済みdigestだけを信用せず、live Gitとmanifestから再導出したimmutable fieldも
個別照合する。異なる内容、別plan ID、同じIssue/role/round/task/worktreeのactive entryとの衝突は拒否する。

runtime親AIがsupervisorへ渡す値は従来どおりIssue、role、change-plan ID、fixer roundの4項目だけである。
control-plane CLIのworkspace/source/approver/protected pathは発行時だけの入力であり、runtime launchへ転記しない。

attemptはowner PID/start-token、intent digest、leaseを持つ。生存processは時刻だけで奪わない。
rate limitまたは登録済み診断pauseからのresume threadは親入力を禁止し、ledger lock内のlatest
`paused_rate_limit` / `paused_karte_registered` attemptとentry `agent_id`が一致するときだけ自動導出する。run時にpauseが残れば
`RESUME_REQUIRED`、resume時のmissing/old/later failure/active/mismatchは拒否する。

Popen直前に同じ4入力からintentを再読し、全field/evidence digest、latest reservation、owner process identity、
live Git、generated profile/runtime/executables/role digestと実commandを再検証する。不一致時はPopenせずfailed
attemptを残す。latest reservation、owner PID/start-token、intent digest、live Gitの最終検査から、
`Popen`が返したchild PID/start-tokenを`spawned`として同じ台帳へ記録するまで、同一ledger lockを保持する。
記録直後にlockを解放し、model実行中は保持しない。Popen・callback・台帳書込の例外でも`finally`で解放する。
lock FDはCLOEXECかつPopenは`close_fds=True`なのでchildへ継承しない。ledger協調writerはこの区間を越えて
更新できない。同UIDでprivate control rootを書換えられる非協調host processは既存threat boundary外である。

### command境界の縮小

full MCP command broker、command毎fresh-bwrap、Landlock EXECUTE allowlist、空procfs、broker
request/CAS ledger、installed CLI feature catalog完全一致は採用しない。innerはbuilt-in commandを
workspace-writeで直接使い、data-plane networkをdenyする。親control processはtask-scoped authと
model API control-planeを使用できる。

nested Codexについてはmodel/API到達遮断が必要条件である。到達前にlocal `thread.started`が作られる
可能性は残余リスクとして受容するが、それを成功証拠にはしない。model-free検証はfake auth、fake
endpointのhost-local listenerを使い、次を同時に確認する。

- 親からlistenerへ到達できるpositive control
- model-originated command側の接続失敗とlistener request 0
- raw auth env、auth path、installed Codex tree、継承FDがcommand側から利用不能
- workspace内writeのみ成功し、main/common Git/protected roots/private host `/tmp`へのwriteは失敗

未実装時のログ、旧broker経路のログ、local thread生成だけを改訂ACの証拠に流用しない。

PreToolUseはexactな`python3 -m issue_start.codex_supervisor run|resume`の4入力形と先頭`rtk`1個版だけを
dry-runし、追加・重複・compound・env/assignment変形を拒否する。無関係なBashとdirect Codex wrapperは
no-opである。任意shell表現の完全封鎖は全command brokerへ戻るため範囲外であり、hookはauthorityではない。

### permission profile

OpenAI公式設定ではlegacy `--sandbox workspace-write`はwrite/network境界であり、一般のread denyを
表現しない。一方、permission profileはexact path/globの`deny`でread/writeを遮断できるが、
`default_permissions`と`sandbox_mode`/`--sandbox`は併用しない契約である。そのため「literal
`--sandbox workspace-write`を維持」と「auth path/installed treeのread deny」を同時に公式設定だけで
保証できない。raw auth envは`shell_environment_policy.inherit="none"`で遮断できるが、path read denyは
別である。

採用実装は`:workspace`をextendsするtask-private `issue-supervised` profileである。runtime/auth/Codex install
rootをdenyし、networkをdisabled、child shell環境を`PATH=/usr/bin:/bin`だけにする。native Codex実行ファイル
だけをprivate `/run/issue-supervised/codex`へread-only bindして自己re-execを成立させる。model/APIを使わない
active/negative probeでこの実効境界を検証し、検証不能はlaunch前fail-closeする。

### 維持する権限非対称

- implementer: host publishでcommit/push/PR create可、merge不可
- fixer: karte診断後、host publishでcommit/push可、merge不可
- reviewer: review/comment/clean時merge判断可、自己修正/push不可
- protected asset: owner launch planのexact path/base digestに一致するstructured patchだけhost適用
- bootstrap PR: reviewerと処置contextを分離し、明示waiverを記録する

### Fixer host karte bridge（F-452-17）

最初のfixer turnは診断専用で、outer sandboxはworktreeをread-onlyにし、
`tmp/_diagnosis/<task-key>/`だけを書込み可能にする。中央karteと共通Gitは引き続きread-onlyである。
hostは開始前にclean Git snapshot、中央karte digest、launch identityとfinding IDをledgerへ固定し、
innerはhost生成templateを使って同directoryの`proposal.json`へ構造化診断だけを書く。
active model-free probeはこのphaseではworkspace write拒否とproposal directory write成功を同時に検査する。

`turn.completed`とexit 0後に`diagnosis_ready`を記録する。hostは差分なし、proposal identity/digest、
finding/round/targetsと既存karteの類似飽和規則を検査し、中央karteへAttemptを追記する。
ledgerの`karte_bridge`へ先にappend内容・前後digest・Attempt番号・threadを記録し、同directoryの
fsync済みtemporary fileからatomic replaceする。karte CLIのmutatorと同じwriter lockを使う。
成功後は`paused_karte_registered`とし、同じ4入力の`resume`だけが同一threadを再開する。
resume時の中央karte・proposal・Attempt不一致は拒否する。登録中に停止した場合は同じresumeが
`diagnosis_ready`からhost登録を冪等復旧してから再開する。別threadやfresh runへ置換しない。

修正後handoffは登録済み診断とfinding/round/宣言targetsに一致しなければpublish不可である。
fixer publish順は`add → commit → push → karte.close-attempt → final`とする。close actionの追加引数は
禁止し、中央Attempt、launch時の編集前OID、push済みHEADからhostがResultと実測touchedを生成する。
pushだけではfinalにならない。closeにも前後digest付きjournalを使い、push後・Result前後・completed後・
final前後の停止は重複push/Attempt/Resultなく収束する。異なるdigestやschema-validな置換も拒否する。

判断: 既存karte CLIへ任意のhost権限を渡す方式ではなく、host専用のappend/close transactionを追加した。
既存CLIの類似飽和・型検査とtouched抽出を再利用し、通常CLIの処置契約は維持する。
writer lockは協調writer間の排他であり、same-UID非協調host processは既存threat boundary外である。
このbootstrap実装・unitは正規transport/P4成功の証拠ではなく、merge後同一baselineでのP4を別途要求する。

### 残す記録と退役物

`tests/reports/`と`tests/logs/`の既存F-452記録は歴史証拠として変更しない。active code/docsからは
prepare/brokerを除く。`worktree_ledger.py`、`durable_lock.py`、supervisor session/attempt/publish ledger、
JSONL observer、protected patch、private `/dev`、host publish recoveryは維持する。

## 移設元: `.codex/hooks/README.md`

冒頭の hook 一覧の3番目に次の項目があった。

3. A Bash `PreToolUse` hook (`codex-launch-intent-gate.sh`) that shape-checks the
   exact minimal-input supervisor command before the authoritative runtime checks.

「PreToolUse command gate」節の冒頭は次のとおりだった。

Issue #452 で Codex workspace-binding transport と all-tool binding hook は退役した。
`spawn_agent` の implementer/fixer は issue-start gate が常時
`ISSUE_START_TRANSPORT_UNAVAILABLE` で拒否し、正規経路は repo supervisor の別 process に限る。

### Codex supervisor launch-intent gate

親AIが手入力できる正規commandは次の4値だけである。

```text
python3 -m issue_start.codex_supervisor (run|resume) --issue N --role ROLE --change-plan-id ID [--fixer-round N]
```

repository/workspace/branch/OID/task key/handoff/protected plan/model/effort/executable/runtime/profile/promptは
`managed-entrypoints-v2.json`、host main worktreeのprivateな
`tmp/_codex_control/change-plans/<ID>.json`、canonical worktree ledger、live Gitから同じgeneratorが
導出する。owner approvalはhost control-planeの運用記録であり、個人の暗号学的な本人証明とは称さない。
inner agentがchild workspaceへ置いた同名planはauthorityにならない。

production stateはowner承認後に`python3 -m issue_start.codex_launch_control issue`で発行する。このCLIは
PreToolUse launch hookの対象ではないcontrol-plane専用入口で、登録済み`.worktrees/*`とcapture済み構造化sourceを
受ける。worktree作成とGitHub captureはcaller責務であり、issuerはnetwork/model/Claudeを使用しない。
ledger pending→sources→ledger complete→planの順で公開し、partial stateはlaunchが拒否、同一要求retryが修復する。

network denyのinner processでもACを読めるよう、change planはprivate control root内の構造化Issue/AC
snapshotについてpath、SHA-256、取得元・取得時刻・取得主体を保持する。fixerは構造化karte snapshotの
exact roundとopen finding IDも必須である。generatorは同じFDで検査・読取したsnapshotのdigestと意味を
照合してpromptへ展開し、URLだけをtask promptとはみなさない。private rootはcurrent-user所有0700、
fileは0600/single-linkを要求し、各componentをdirfd/openat/O_NOFOLLOWで辿る。PreToolUseは実行前に
同generatorをdry-runし、型・値域・role/round/Issue/AC/karte整合、host approval record、canonical
ledger/live Git、manifestのmodel/effort/profile/template/path、実行ファイルのowner/mode/digest/versionを
fail-close検査する。raw commandと先頭に`rtk`を1個置く形だけが正規形であり、fieldの順序・個数も
上記どおり固定する。追加・重複field、compound command、`env`・assignment・別wrapperによる変形は
拒否する。無関係なBashとdirect `codex exec`はこのhookの対象外である。

このhookは早期フィードバックでありauthority/receiptではない。supervisor自身が4入力以外を受け取らず、
process起動直前に同じrequestからintentを再生成してplan/manifest/Issue/karte/ledger/role/executable/Gitと
実command/profileを再照合する。change-planのowner側永続化とcanonical ledger entryの発行はhost control
planeの責務で、同entryへimmutable intent digestとattemptを追記し、第2entryを作らない。
snapshot/change-planを作るcontrol planeはmodel-originated write surfaceの外に置かなければならない。

任意のshell wrapperや別interpreterに隠したdirect Codex起動をPreToolUseで完全封鎖することは範囲外である。
それを行うには全commandのshell解析・pre-exec brokerへ戻る必要があるため、既知の残余リスクとして受容する。

### Files 表の行

| File | Role |
|---|---|
| `codex-launch-intent-gate.sh` | Bash PreToolUse handler. Resolves the main worktree from `--git-common-dir`, then runs `python3 -m issue_start.codex_launch_intent hook` to shape-check the exact minimal-input supervisor command (see "Codex supervisor launch-intent gate"). Early feedback only, not the authority; unrelated Bash and direct `codex exec` are out of scope. |

## 移設元: `docs/tools/issue-start-and-branch-source.md`

「Managed Issue-start」節で、Codex の parser 退役を述べた段落の末尾は「Codex正規経路はrepo supervisorの別processである。」
だった。続く段落は次のとおりだった。

repo supervisorの公開`run|resume`は`--issue`、`--role`、`--change-plan-id`とfixer時だけ
`--fixer-round`を受ける。host issuerが作るprivate change planは`ledger_entry_id`を持ち、そのentryは
`platform=codex-supervisor`でなければならない。runtimeは同entryへimmutable intent digestとattemptを
追記し、Popen直前にcanonical stateとlive Gitを再読する。change-plan/Issue/AC/karteを発行するhost
control-planeは`python3 -m issue_start.codex_launch_control issue`で発行する。既存host provisioningが
`.worktrees/*`へ登録済み専用worktreeを用意し、callerがGitHubから構造化Issue/AC snapshot（fixerはkarteも）を
captureした後に呼ぶ。issuer自身はworktree作成、GitHub取得、model/API呼出しを行わない。発行済みstateがない、
またはledgerが`issuance_status=complete`になる前の状態ではruntimeはfail-closeする。

## 移設元: `.ai/agents/issue-implementer.md`

「入力」節の `handoff_path` の説明には、次の括弧書きが付いていた。

（Codex supervisedではmanifestのhandoff_templateとcanonical ledgerからhostが導出し、promptへexact 1回だけ注入）

同節の「handoff_path がなければ実装に着手せず STOP する。ファイル名は自分で決めない。」には次の文が続いていた。

Codex supervisor経路では親AI/CLIの自由入力を受けず、manifestのrole別handoff_templateをcanonical ledgerと照合したhost導出値だけがpromptにexact 1回提示される。

続く段落は次のとおりだった。

Codex supervisorのrole promptには、handoff_pathに加えて `branch_name`、`repository`、`expected_oid` も `Host-derived execution facts` としてhostが提示する。4値はcanonical ledgerとlive Git factsから導出され、親runtimeの入力には追加しない。innerは提示されたhandoff_pathだけへ書き込み、snapshot本文に現れる実handoff file candidateやhost authority/prompt reserved placeholderを権威値として扱わない。bareな`tmp/_handoff/`説明、reservedでない一般placeholder、通常コード断片は単一format passのsnapshot dataとして許可される。

「出力とハンドオフ」節には、ハンドオフ構造の前に次の2段落があった。

`CODEX_ISSUE_SUPERVISED=1` のinner processではcommit/push/PRを行わず、host publish前の
JSON-compatible schema v1 handoffを書く。`phase`は`pre_publish`、成功時`status`は`ready`とし、
hostから束縛されたrole、Issue、task key、branch、現在HEAD、結果を含める。STOPは`status: stopped`とし、
hostはpublish不可として扱う。下記の`pr_opened`形式はhost publish完了後のfinal phaseであり、inner成功証跡に流用しない。
`result`は`changed_files`、`tests`、`out_of_scope_findings`、`protected_patch`の4 fieldだけとする。
protected asset変更がなければ`protected_patch`はnull、ある場合はstaging patchの相対`path`と`sha256`を入れる。
hostはsupervisor run時にownerがimmutable launch recordへ記録したexact protected pathとbase SHA-256だけを承認し、promptや
publish CLIでpath/digestを追加しない。protected patch（宣言時のみ）→add→commit→push→PR createを
順番に実行し、最終handoffを生成する。

同inner processはworkspace-write相当の境界でdirect `codex exec -C`を実行し、literal `--sandbox`は使用しない。data-plane networkと
raw auth envを利用せず、nested Codexのmodel/API到達を試みない。local thread生成だけは成功証拠に数えない。

ハンドオフ構造の2行目には `phase: final` があった。inner が書く `pre_publish` と host publish 後の `final` を
区別する項目であり、区別対象が退役した後は読み手も検証者も無いため、レビュー是正（F-538-05）で構造から除いた。

## 移設元: `.ai/agents/issue-fixer.md`

「入力」節の `handoff_path` の説明には、次の括弧書きが付いていた。

（Codex supervisedではmanifestのhandoff_templateとcanonical ledgerからhostが導出し、promptへexact 1回だけ注入）

同節の「渡された値から別の値を組み立てない。」には次の文が続いていた。

Codex supervisor経路では親AI/CLIの自由入力を受けず、manifestのrole別handoff_templateをcanonical ledgerと照合したhost導出値だけがpromptにexact 1回提示される。

続く段落は次のとおりだった。

Codex supervisorのrole promptには、上記4値を `Host-derived execution facts` としてhostが一括提示する。`handoff_path`、`branch_name`、`repository`、`expected_oid` はcanonical ledgerとlive Git factsから導出され、親runtimeの入力には追加しない。innerは提示されたhandoff_pathだけへ書き込み、他のsnapshot本文に現れる実handoff file candidateやhost authority/prompt reserved placeholderを権威値として扱わない。bareな`tmp/_handoff/`説明、reservedでない一般placeholder、通常コード断片は単一format passのsnapshot dataとして許可される。

「出力とハンドオフ」節には、ハンドオフ構造の前に次の2段落があった。

`CODEX_ISSUE_SUPERVISED=1` のinner processではJSON-compatible schema v1 handoffを使う。
この実行形態ではStep 0のbranch取得とStep 1/2の中央karte書込み・commit/pushはhostの責務である。
最初のturnは診断専用で、worktree全体はread-only、hostが示すtask-private診断directoryだけがwrite可能である。
host生成promptにあるschema v1 `diagnosis_proposal`のidentity/finding_ids/karte_sha256をそのまま用い、
root_cause/change_kind/targets/diagnosisを埋めて指定proposal.jsonへ書き、終了する。コード編集とpre_publish作成はまだ行わない。
hostが中央karteへAttemptを登録した後、同じthreadのresumeで渡される
登録receiptのAttempt番号、targets、root_cause、change_kindを採用してからStep 2の編集・testへ進む。
scope変更は既存proposalの書換えで通さずSTOPしてhostへ返す。
`phase`は`pre_publish`、成功時`status`は`ready`とし、hostから束縛されたrole、Issue、task key、branch、
現在HEAD、結果を含める。STOPは`status: stopped`とし、host publish不可として扱う。下記形式はhost publish後のfinal phaseである。
`result`にはfinal生成に必要なround、既存PR URL、finding_ids、diagnosis、outcome、changed_files、tests、
unresolved_findings、out_of_scope_findings、protected_patchを過不足なく入れる。protected asset変更がなければ
`protected_patch`はnull、ある場合はstaging patchの相対`path`と`sha256`を入れる。承認対象pathはsupervisor
run時にownerがimmutable launch recordへpathとbase SHA-256を記録し、promptやpublish CLIから追加しない。hostはprotected patch
（宣言時のみ）→add→commit→push→karte.close-attemptを順番に実行し、final handoffを生成する。

同inner processはworkspace-write相当の境界でdirect `codex exec -C`を実行し、literal `--sandbox`は使用しない。data-plane networkと
raw auth envを利用せず、nested Codexのmodel/API到達を試みない。local thread生成だけは成功証拠に数えない。

ハンドオフ構造の2行目には `phase: final` があった。inner が書く `pre_publish` と host publish 後の `final` を
区別する項目であり、区別対象が退役した後は読み手も検証者も無いため、レビュー是正（F-538-05）で構造から除いた。

## 移設元: `.ai/Individually-managed-lists.md`

「PF 固有の実行差分」の Codex の行は、登録 hook として `agent-command-gate.sh`・`issue-start-gate.sh`・
`codex-launch-intent-gate.sh` の3つを挙げ、「ライフサイクル hook 一覧」の行 1・3・12 を参照していた。
同一覧の12行目と、対応する概要は次のとおりだった。

| # | ライフサイクル hook | 呼び出し実体 | Claude Code | Codex CLI | Copilot |
|---|---|---|:---:|:---:|:---:|
| 12 | PreToolUse（Bash） | `codex-launch-intent-gate.sh` | — | ✅ | — |

### 12. codex-launch-intent-gate

- **概要**: 親 AI が手入力する Codex supervisor 起動コマンド（`python3 -m issue_start.codex_supervisor (run|resume) --issue N --role ROLE --change-plan-id ID [--fixer-round N]`）の形を、実行前に host 導出の launch intent と照合して fail-close で検査する。早期フィードバックであり権威（authority／receipt）ではない。supervisor 自身が process 起動直前に同じ request から intent を再生成して再照合する。
- **スコープ**: PreToolUse（Bash）。無関係な Bash と direct `codex exec` は対象外。Codex 専用。
- **実装構成**: `.codex/hooks/codex-launch-intent-gate.sh`（main worktree を `--git-common-dir` から解決して `python3 -m issue_start.codex_launch_intent hook` を起動する薄いラッパー。実体は `issue_start/codex_launch_intent.py`。`.codex/hooks/README.md` の「Codex supervisor launch-intent gate」節にも概要あり）

## 移設元: `issue_start/managed-entrypoints-v2.json`

top-level block `codex_supervisor_launch` は次のとおりだった。`managed`・`isolation_only`・`unmanaged` は変更していない。

```json
"codex_supervisor_launch": {
  "schema_version": "codex-launch-intent/1",
  "change_plan_schema": "codex-change-plan/2",
  "change_plan_root": "tmp/_codex_control/change-plans",
  "canonical_ledger_platform": "codex-supervisor",
  "reservation_contract": "same-entry/intent-digest-v1",
  "issuer_contract": {
    "schema_version": "codex-change-plan-issuance/1",
    "command": "python3 -m issue_start.codex_launch_control issue",
    "sources_root": "tmp/_codex_control/sources"
  },
  "roles": {
    "issue-implementer": {
      "model": "gpt-5.6-sol",
      "reasoning_effort": "xhigh",
      "task_key_template": "issue_{issue}",
      "handoff_template": "tmp/_handoff/issue-implementer--issue-{issue}.yaml",
      "prompt_template": "Implement Issue #{issue} under owner-approved change plan {change_plan_id}. Host-derived execution facts (write only this exact handoff path): handoff_path={handoff_path}; branch_name={branch_name}; repository={repository}; expected_oid={expected_oid}\n\nVerified Issue and Acceptance Criteria snapshot follows:\n\n{issue_snapshot}"
    },
    "issue-fixer": {
      "model": "gpt-5.6-sol",
      "reasoning_effort": "xhigh",
      "task_key_template": "issue_{issue}_fix_r{round}",
      "handoff_template": "tmp/_handoff/issue-fixer--issue-{issue}-r{round}.yaml",
      "prompt_template": "Fix findings {finding_ids} for Issue #{issue} under owner-approved change plan {change_plan_id}. Host-derived execution facts (write only this exact handoff path): handoff_path={handoff_path}; branch_name={branch_name}; repository={repository}; expected_oid={expected_oid}\n\nVerified Issue and Acceptance Criteria snapshot follows:\n\n{issue_snapshot}\n\nVerified finding karte ({karte_path}) follows:\n\n{karte_snapshot}"
    }
  },
  "executables": {
    "bwrap": "/usr/bin/bwrap",
    "codex": {
      "lookup_name": "codex",
      "sandbox_alias": "/run/issue-supervised/codex"
    }
  },
  "runtime_root_template": "tmp/_codex_sessions/{task_key}/runtime-home",
  "permission_profile": "issue-supervised"
}
```

## 移設元: `issue_start/gate.py`・`issue_start/worktree_ledger.py` の説明文

`issue_start/gate.py` の module docstring は、Codex の deny 理由を次のように説明していた。

Claude transport は marker 契約を維持する。Codex の ``spawn_agent`` transport は
per-subagent workspace を指定・観測できないため、既知 implementer/fixer dispatch を
payload の詳細検証より先に常時 deny する。Codex supervisor はこの gate とは別経路である。

`ISSUE_START_TRANSPORT_UNAVAILABLE` の detail は
`harness=codex; per-subagent workspace selection/observation unavailable` だった。
reason code と deny の発火条件は退役の前後で変わっていない。

`issue_start/worktree_ledger.py` の `latest_open_entry` は、`platform` で絞る理由を次のように説明していた。

Codex supervisorは`.worktrees/`配下と独立launch recordを使う。ここへ混ぜると
Claude ``SubagentStart`` がCodex supervisor entryを横取りするため、
platform 欠如（既存 entry）または ``claude`` だけを対象にする。

## 移設元: `.ai/troubleshooting/codex-review.md`

レビュー是正（F-538-02）で移設した。「CLI または認証が利用できない」節の末尾に次の段落があった。

repo supervisor経路ではcanonical `~/.codex/sessions`を直接共有せず、main worktreeの
`tmp/_codex_sessions/<task-key>/sessions`を同じmount先へtask単位でbindする。initial/resumeでmarkerが
継続しない場合は、このsourceの欠落・symlink・modeとouter commandの`--bind`を確認し、fresh threadへ置換しない。
clean hostではsupervisorが非symlinkの`~/.codex/sessions` targetを作成するため、未存在を手作業で事前作成せず、
作成失敗reasonとHOMEの所有権を確認する。workspace shellからtask markerを書換できた場合は隔離失敗として停止する。
