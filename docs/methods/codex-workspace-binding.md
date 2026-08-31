# Codex Issue workspace durable binding 判断記録

Status: adopted（repo-supervised Codex subprocess）  
Date: 2026-08-30

## 問題と現行保証

Claude の `issue-implementer` / `issue-fixer` は Agent tool の `isolation: "worktree"`、
SubagentStart/Stop、ownership ledger、collect/release により `.claude/worktrees/agent-*` へ束縛される。
Codex は `collaboration.spawn_agent` に `cwd` / `workspace` / `isolation` 引数がない。
spawn の PreToolUse `cwd` は main-thread の turn/session cwd であり child cwd ではなく、
各 tool の PreToolUse も `exec_command.workdir` を含まない。さらに current payload は actual
agent identity と spawn 成功観測を信頼済み値として与えない。したがって次の4値は、
実 transport が提供するまで機械保証できない。

- child workspace
- 各 tool の実効 workspace
- actual agent identity
- spawn 成功

権限面では既に `agent-command-gate.sh` が implementer/fixer の push 可・merge 不可、reviewer の
push/自己修正不可を機械化している。この非対称と Claude isolation lifecycle は変更しない。

## 採用方式

主文脈が agent 起動前に、main worktree の `tmp/_worktree/ledger.json` へ次を `platform: codex` の
`open` entry として記録する。

- Issue、round、repository、専用 workspace、branch、expected OID
- role、handoff_path、平文 task key
- prepared_at、expires_at、agent_id/collected_to を含む ownership lifecycle

task key は implementer が `issue_<N>`、fixer が `issue_<N>_fix_r<R>` の canonical form とする。
prepare は workspace が main 配下の `.worktrees/<1要素>` であり、`git worktree list --porcelain` に
登録済みで、origin/branch/HEAD が指定値と完全一致する場合だけ `open` entry を作る。
この entry は単独では「dispatch された」証拠ではなく、repo supervisor が process/threadを観測するまで
prepare-only 記録である。

`collaboration.spawn_agent` の Codex implementer/fixer transport は引き続き `availability: unavailable` とし、既存の
trusted issue-start PreToolUse hook が `ISSUE_START_TRANSPORT_UNAVAILABLE` で dispatch を拒否する。
新設 all-tool hook が未 trust で実行されなくても、dispatch 自体がこの既存 hook で止まる。

恒久経路は `issue_start.codex_supervisor` とする。host側supervisorが検証済みbindingのIssue専用worktreeで
別 `codex exec` processを起動し、次の二段境界を適用する。

- 外側bubblewrap: `/`、main checkout、共通Git領域をread-only、対象worktreeだけwriteable、`/tmp`をprivate
  tmpfsにする。Codex制御processのAPI通信は維持し、model生成toolのdata-plane networkは内側の
  `network_access=false`、web/apps無効化、禁止event監視で別に拒否する。Python/Codexの起動に必要なOS entropyは`/dev/urandom`だけを
  `--dev-bind`した直後に`--remount-ro`し、`--dev /dev`でdevice集合やwrite範囲を広げない。通常の
  `--ro-bind`はnested user namespaceでdevice accessを保証しないため採用しない。
- 内側Codex: `workspace-write`、approval `never`、user config無視、web search disabled、shell network false、
  multi-agent disabled、apps disabledを明示し、model `gpt-5.6-sol` / reasoning `xhigh`を固定する。hostはmain
  canonicalのprotected role wrapperとcommon本文をbundle化し、対象branchの同bundle digestが一致した場合だけ
  developer instructions、`CODEX_ISSUE_ROLE`、digestを束縛する。task promptや対象PRの変更をrole identityとして採用しない。
- canonical `~/.codex` の認証・configはread-onlyのまま、main `tmp/_codex_sessions/<task-key>/sessions`だけを
  `~/.codex/sessions`へwrite bindする。Codex制御processはrolloutを永続化でき、inner workspace shellはCodex
  sandboxによりworkspace外のsession stateを書き換えられない。clean hostではhost supervisorが非symlinkの
  `~/.codex/sessions` mount targetを先に作成し、initial/resumeは同じtask directoryを再利用する。
- `.git`、`.codex/**`、`.agents/**`、実行roleの`.ai/agents/<role>.md`は対象worktreeのwrite bindより後にread-onlyで再mountする。変更が必要な
  場合はinner processがstagingへschema v1 patchを出す。exact pathはbinding prepare時の
  `--protected-path`でmain ownership ledgerへowner planとして先に記録し、publish CLIやpromptから追加しない。
  hostがこのdurable plan、base SHA-256、
  path traversal、symlink、件数・サイズを検証してatomic applyする。
- inner processは編集・テスト・handoffだけを行う。commit/push/PRはexit後にhostがrole別allowlistと既存
  `gitgate`を通して行い、implementer/fixerにmergeを許可しない。

inner handoffはJSON-compatible schema v1の`pre_publish` phaseとし、ready、role、Issue、task key、branch、
現在HEADとrole別result schemaをhostが完全照合する。STOP、任意の非空file、host publish後のfinal handoffとは
区別する。implementer finalは`pr_opened`と検証済みPR URL、fixer finalは`fixed`とround/PR/finding/diagnosisを含む
既存consumer schemaへhostが生成し、同じrole別validatorを通す。

Codex公式のnon-interactive契約に従い、stdout JSONLの`thread.started`を1件だけ受理する。supervisorは
OS PIDと`/proc/<pid>/stat`のprocess start tokenを先に記録し、同一attemptの`thread.started`を観測してから
初めてledgerを`running`へ束縛する。`turn.completed`、exit code 0、正規handoffの3条件が揃った場合だけ成功とする。
JSONL欠落・重複・破損、禁止tool event、`turn.failed`、非0 exit、timeout、kill、handoff不正はfail-closeし、
worktreeとreasonを非終端entryに保持する。rate limitは同じrole/model/reasoning/thread/worktreeのresume planだけを
返し、品質降格やfresh threadへの置換をしない。

supervisor start 前の binding 検証は非破壊とし、`open -> running` には遷移させない。
residue deny、blocker deny、API failure、router failure の後も agent/handoff 不在の entry を
`running` に永久消費しない。TTL 内は同じ entry を再検証し、TTL を越えた `open` は同一 canonical
task・repository・workspace・branch・OID・handoff・role・roundの場合だけ、台帳ロック下で同じ entryを
新しいTTLへ原子的にrefreshする。旧prepared/expires時刻は `refresh_history` に残す。別identity、期限内の
二重prepare、running/terminal taskは従来どおりdenyする。

supervisor自身がtrusted start observerとなり、actual thread ID、workspace、PID/start tokenを同時に記録して
identityを1度だけ`running`へbindする。resumeはrole/workspace/thread一致を必須とし、stale threadを拒否する。
成功handoffだけをcollect/releaseへ渡す。start/resumeはledger lock下でattemptを予約し、supervisor owner
PID/start tokenが生存する限りlease期限後も二重起動を拒否する。owner終了後のlease回収では新fencing tokenを
発行し、旧attemptのspawn/running/terminal eventをCAS拒否する。resumeは最新eventが同一threadの未消費`paused_rate_limit`の場合だけ
許可する。CLIの`run`/`resume`がこの入口を呼び、`publish`は最新success、handoff、fresh Git facts、role allowlistを
再検証する。protected patch（宣言時のみ）→add→commit→push→implementerのPR createをowner PID/start tokenと
lease付きでledger順序予約する。owner crash後は期限切れreservationを回収し、実行済み効果をGit factsから
保守的に照合する。各completed eventのHEAD/index tree/worktree/upstream snapshotを次段のexpected値へCAS束縛し、
cleanなHEAD差替えも拒否して固定`gitgate`/`gh pr create` executorだけを呼ぶ。

## 却下案

- 暗号化 message の復号・解析: hook が信頼できる平文として観測できず、transport 実装にも依存する。
- task name と cwd だけの都度導出: round/handoff/branch/OID/ownership と task 再利用を証明できない。
- 環境変数や一時的な親プロセス状態: durable でなく、agent command から同じ値を検証できない。
- fixer を worker/implementer として起動: karte の書き手、push/merge、レビューと修正の役割分離を壊す。
- Codex 用に Claude ledger/lifecycle を置換: 稼働済み isolation、SubagentStop、residue deny を退行させる。
- Codex本体、`spawn_agent` schema、runtime hook payloadの変更: 本repoはCodex本体の開発・配布主体でなく、
  owner決定により将来も恒久候補外とする。
- 内側Codexへcommit/pushを許可: `.git` writeと認証情報をモデルprocessへ渡し、role別publish gateを迂回する。

## Security trade-off と限界

ledger は暗号学的署名ではなく、main worktree のファイル境界、host supervisor、OS mount/network namespaceを
信頼境界にする。inner Codexはworktree内容を変更できるためhandoffやpatch内容自体は信頼せず、hostがpath、digest、
Git factsを再検証する。bubblewrap/user namespaceが利用できないhostでは保護を弱めて起動せず、P1 probeをfail-closeする。
Codex API通信自体はmodel利用に必要だが、model-generated shellのnetworkとweb searchは別に無効化する。
P1のwrite/network probe payloadはcoverageやvenvのruntime差を混ぜない固定`/usr/bin/python3`を使う。host `/tmp`
sentinelの不可視性とhost local listenerへの到達不能を測り、各isolationを個別に外したnegative controlが必ず失敗する
ことも確認する。実Codex runtimeは
同じouter commandの`codex --version`をmodel無呼出で起動し、device/mount構造testと分けて確認する。

## bootstrap PR の finding 方針

本機構を導入する PR 自身の独立レビューで finding が出た場合、未導入 supervisor/fixerを別roleへ偽装して
起動しない。finding と再確認方法を記録してSTOPし、merge前修正が不可避な場合だけオーナーが明示したbootstrap
処置を別記録にする。同じreviewer文脈を修正担当にせず、この例外を正規supervised fixerの証拠として扱わない。

## 後続影響確認

PR #453 merge後の影響確認は完了した。PR #449/#374とPR #448/#407はfinding解消・独立再レビュー後にmerge/close済み、
PR #451はWave 0 baseline draftとして変更不要・open維持である。supervisor実装PRは独立reviewとP2〜P4のlive evidenceを
確認するまでIssue #452を自動closeしない。#445にはsupervised Codexが#374/#407/#371をblockしないowner決定を保持する。

## 検証段階

- P0: fake runnerで正常、JSONL欠落・重複・破損、非0 exit、timeout、kill、handoff不正、禁止tool、rate-limit pause/resumeを検証。
- P1: modelを呼ばず、worktreeだけwrite可、main/共通Git/`.codex`/`.agents` write不可、private tmp、network不可を実測。
- P2: 最小1-turn・編集なしのlive CodexでPID/start tokenから正常終了まで確認。
- P3: worktree markerだけ許可し、main/`.git`/network/nested Codexを拒否するlive確認。
- P4: implementer/fixer各1件でhandoffとhost publish planを作り、remote送信前に独立監査する。

P0/P1とunit/integration testは実装PRに含める。P2〜P4を実行する場合はtoken最小prompt・exact expected output・
timeout・停止条件を先に固定し、Claude Codeを使用しない。
