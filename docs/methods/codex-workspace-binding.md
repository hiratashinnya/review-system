# Codex Issue supervisor 実行契約

## 結論

`collaboration.spawn_agent` 用 workspace binding は退役した。OpenAI公式のcustom agent schemaに
per-subagent作業ディレクトリ指定がなく、subagentは親runtime/workspaceを継承するため、repo側の
prepare/TTL/refreshでは実効workspaceを成立・観測できない。Codex本体の上流改修は利用者側の
恒久策に含めない。

既知の`issue-implementer` / `issue-fixer`を`spawn_agent`で起動しようとした場合、issue-start
gateはpayload、cwd、ledger、GitHub APIを読む前に常時`ISSUE_START_TRANSPORT_UNAVAILABLE`で拒否する。
manifestの`binding_transports.codex`、`issue_start/codex_binding.py`、all-tool binding hookは存在しない。
Claude transportのmarker/isolation契約は変更しない。

## 正規Codex経路

正規経路は`issue_start.codex_supervisor`がIssue専用のdurable worktreeで別Codex CLI processを
起動する経路だけである。

1. 親AIが渡せる値はIssue、role、owner-approved change-plan IDと、fixer時のroundだけである。
2. supervisorはhost private change plan、manifest、構造化Issue/AC（fixerはkarteも）、canonical ledger、
   live Git、role contract、permission profile、実行ファイルから残りを一意に導出する。
3. host control-plane issuerが先に作った`platform=codex-supervisor`のcanonical ledger entryを、同じledger lock transactionで
   immutable intent digestとattemptにより拡張する。第2entryは作らない。secure canonical stateが無ければ
   fail-closeする。
4. private `/tmp`/`/dev`、worktree書込限定、main/common Git/protected assets read-onlyのOS境界で
   `codex exec -C <worktree> --sandbox workspace-write`を実行する。
5. PIDと`/proc/<pid>/stat` start tokenを記録し、同じprocessのJSONL `thread.started`を1度だけ束縛する。
6. `turn.completed`、exit 0、schema v1 `pre_publish` handoffを全て確認して初めて成功とする。
7. commit/push/PR createはhost publish state machineが段間Git facts CASを検査して実行する。

## Host control-planeの発行

`python3 -m issue_start.codex_launch_control issue`は、owner承認後にproduction change planを発行する
専用入口である。入力はIssue番号、role、change-plan ID、登録済み専用worktreeの絶対path、capture済みの
構造化Issue snapshot、承認者login、fixerの場合だけroundとkarte snapshot、任意のprotected path名に
限定する。repository、branch、OID、task key、handoff、finding ID、content digest、model、runtimeは入力させず、
live Git、manifest、source内容から導出する。承認者と時刻は監査用の運用記録であり、暗号学的な本人証明ではない。

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
rate limit pauseからのresume threadは親入力を禁止し、ledger lock内のlatest
`paused_rate_limit` attemptとentry `agent_id`が一致するときだけ自動導出する。run時にpauseが残れば
`RESUME_REQUIRED`、resume時のmissing/old/later failure/active/mismatchは拒否する。

Popen直前に同じ4入力からintentを再読し、全field/evidence digest、latest reservation、owner process identity、
live Git、generated profile/runtime/executables/role digestと実commandを再検証する。不一致時はPopenせずfailed
attemptを残す。latest reservation、owner PID/start-token、intent digest、live Gitの最終検査から、
`Popen`が返したchild PID/start-tokenを`spawned`として同じ台帳へ記録するまで、同一ledger lockを保持する。
記録直後にlockを解放し、model実行中は保持しない。Popen・callback・台帳書込の例外でも`finally`で解放する。
lock FDはCLOEXECかつPopenは`close_fds=True`なのでchildへ継承しない。ledger協調writerはこの区間を越えて
更新できない。同UIDでprivate control rootを書換えられる非協調host processは既存threat boundary外である。

## command境界の縮小

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

## permission profile

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

## 維持する権限非対称

- implementer: host publishでcommit/push/PR create可、merge不可
- fixer: karte診断後、host publishでcommit/push可、merge不可
- reviewer: review/comment/clean時merge判断可、自己修正/push不可
- protected asset: owner launch planのexact path/base digestに一致するstructured patchだけhost適用
- bootstrap PR: reviewerと処置contextを分離し、明示waiverを記録する

F-452-17（fixer用host karte bridge）は後続依存であり、この縮小で実装済みとみなさない。

## 残す記録と退役物

`tests/reports/`と`tests/logs/`の既存F-452記録は歴史証拠として変更しない。active code/docsからは
prepare/brokerを除く。`worktree_ledger.py`、`durable_lock.py`、supervisor session/attempt/publish ledger、
JSONL observer、protected patch、private `/dev`、host publish recoveryは維持する。
