---
id: TD-issue-start-452
version: 9
condition: boundary
---

# 目的

現行 Codex runtime では保証済み issue-implementer/fixer transport を宣言せず、既存 trusted hook と
all-tool hook が dispatch/tool execution を fail-close することを検証する。併せて、将来 transport 用の
prepare-only durable binding が spawn 前 failure と TTL 超過後にも安全に再試行でき、既存 Claude
isolation lifecycle と role 権限非対称を退行させないことを検証する。さらにrepo supervisorが別Codex CLI
processのPID/start tokenとJSONL threadを観測し、OS sandboxでIssue専用worktreeだけをwriteableにできることを検証する。

# 前提

- main repository と `.worktrees/<name>` の実 linked worktree を一時領域に作る。
- origin、branch、expected OID、handoff、task key を既知値で固定する。
- wall clock は timezone-aware な固定日時を注入する。

# 手順

1. manifest の Codex implementer/fixer transport が `availability: unavailable` であることを確認する。
2. 既存 trusted issue-start hook が両 role の dispatch を `ISSUE_START_TRANSPORT_UNAVAILABLE` で拒否し、
   prepare-only entry を `open` のまま保つことを確認する。
3. all-tool hook が対象 role を turn cwd にかかわらず `CODEX_BINDING_TRANSPORT_UNAVAILABLE` で拒否し、
   対象外 role だけを素通しすることを確認する。
4. blocker/residue/API/router failure 後に TTL を越えた `open` を、同一 canonical task・同一 dispatch
   identity で再prepareし、同じ entry id、更新TTL、`refresh_history` を確認して非破壊validateする。
5. 別identity、期限内または同時の二重prepare、running/terminal task、別cwd/origin/branch、stale OID、
   未登録worktree、欠落handoffを個別に作り、固有reasonで拒否されることを確認する。
6. dormantな将来APIの単体状態遷移として trusted identity bind、command verify、handoff collect/releaseを
   確認する。この手順を現行 spawn transport の保証とは扱わない。
7. 全 unittest、asset parity、既存 agent-command gate/Claude SubagentStop 回帰を実行する。
8. P0 fake runnerで正常、thread/terminal欠落・重複、JSONL破損、非0 exit、timeout、kill、rate limit、
   禁止tool event、handoff不正を作り、PID/start token記録後かつ`thread.started`後だけ`running`になることを確認する。
9. rate limit後のresume commandが同じrole/model/reasoning/thread/worktreeを維持することを確認する。
10. modelを呼ばないP1 bubblewrap probeで、対象worktreeだけwrite可、main/共通Git/`.codex`/`.agents`は
    write不可、`/tmp`はprivate、shell network不可であることをhost側実測する。Python起動に必要な
    `/dev/urandom`だけを`--dev-bind`直後に`--remount-ro`し、device集合やwrite範囲を追加しないことも
    command順序の契約で確認する。payloadは固定`/usr/bin/python3`を使ってcoverage/venv差を除外し、同じouter
    sandbox内の`codex --version`も利用可能なhostでmodel無呼出確認する。
11. protected patchはowner-approved exact path、schema、base SHA-256、path traversal/symlink/sizeをhostが
    検証し、apply直前にもdigestを再確認し、既存permission bitsを保持することを確認する。
12. Codex API control-planeはouter network namespaceで遮断せず、inner tool data-planeはCodex sandbox設定で
    拒否する。protected role wrapperがdeveloper instructionsへ固定され、task promptのrole差替えを採用しない。
13. handoffはschema v1のpre-publish ready/STOP/finalを分離し、role/Issue/task/branch/HEAD/resultを照合する。
    active attempt reservationを並行start/resumeで競合させ、最新の未消費rate-limit pauseだけresume可能とする。
14. process token、spawn ledger callback、stdin初期化の例外でchildをkill/waitし、process identity未観測時は
    bindingをopenのまま保つ。P1はhost tmp sentinel/local listenerを使い、各isolationを外したnegative controlが
    必ず失敗することを確認する。
15. CLI run/resumeからPopen直前まで、fake successからpublish dry-runまで到達し、最新success、handoff、fresh
    Git facts、role allowlistを満たす固定gitgate/gh executor以外を拒否する。
16. host mainのwrapper+common bundleと対象branchのdigestを両roleで比較し、nameを維持したinstructions/common
    改竄もPopen前に拒否する。task専用sessions mountへmodel-free fake Codexがinitial markerを保存し、別processの
    resumeが同じmarkerを読めることを確認する。
17. pre-publish resultとimplementer/fixer finalを別schema validatorへ通し、PR URL欠落、wrong status、STOP、
    任意resultを拒否する。protected patch（宣言時のみ）→add→commit→push→implementer PR createをledger順序、
    staged/clean/HEAD/upstream/URLで確認し、direct push、dirty PR create、未適用patchを拒否する。
18. initial/resume双方で旧runnerをlease期限後まで停止し、live owner中は新reservationを拒否する。owner終了後に
    新fenceを取得したら旧attemptのspawn/running eventをCAS拒否し、新ownerだけが進行することを確認する。
19. publish action直前/直後のowner crashを予約leaseとGit snapshotで回収し、add後のclean commit差替えを
    HEAD/index tree CASで拒否する。protected exact pathはbinding prepare時のowner planだけから読み、publish
    CLIによる追加を拒否する。
20. `.codex/sessions`未作成のclean HOMEでinitialと別process resumeを通す。model-free `codex sandbox` shellは
    task markerの作成・変更・削除を拒否され、outer Codex control processだけが同じmarkerを保存できることを確認する。
21. protected owner planにexact pathとbase SHA-256を一体保存し、patch内digest差替えを拒否する。同じporcelain
    statusを保つworktree内容差替え、同一parentだがpre-indexと別treeのcommitをcrash recoveryで成功扱いしない。
22. gh.pr.create成功後・finish前のcrashをfake GitHub factsで再現し、repository/head/base/head OID/owner/open/non-draftが
    一意一致するPRだけを回収する。final handoff書込前後の両方で同じURLへ冪等完成し、別base等は拒否する。
23. implementerのexisting exact PR回収とfixer pushで、`completed`記録直後・final handoff atomic replace前のcrashを
    注入する。再開時にimplementerはfresh PR factsを再照合し、fixerはupstream/headを再照合する一方、PR create/pushを
    再実行せず同じrole別finalへ収束し、handoff保存後だけ`finalized`を記録する。final済み再実行も同じ結果を維持する。
24. publish reservation、completed、finalized間でcanonical pre-publish/final intent digestを追跡する。両roleの
    completed後・final前にchanged files、tests、out-of-scope findings、finding IDs、diagnosis、outcomeをschema-validに
    差し替えてもfail-closeし、PR create/pushを再実行しない。final保存後のschema-valid差替えも同様に拒否する。

# 期待結果

- 現行 Codex implementer/fixer dispatch は常に unavailable deny となり、正規起動可能とは宣言しない。
- all-tool hook も trusted effective workspace/agent identity/spawn成功観測が無い限り常にdenyする。
- spawn前失敗の `open` はTTL内に再検証でき、期限後は同一identityだけが原子的refreshできる。
- refreshはentryを増やさず旧prepared/expires時刻を監査履歴へ残し、別identity・二重prepare・
  running/terminal taskはdenyを維持する。
- implementer/fixer push可・merge不可、reviewer自己修正不可、Claude isolation/collect/release/residue deny が維持される。
- `collaboration.spawn_agent`はunavailableのまま、別process supervisorだけがCodex実装roleの正規経路となる。
- JSONL、process、Git facts、handoffの一つでも不正なら成功にせず、回収可能な非終端ledger entryを保持する。
- inner processはcommit/push/PR/mergeを持たず、host publish allowlistがimplementerとfixerの非対称を維持する。
- start/resumeは一意attemptへ直列化され、pre-publish handoffからhost publish後finalへのphase遷移が監査できる。
- 対象PR自身はtrusted role contractを変更できず、session rolloutはtask間で共有されずresume間だけ永続する。
- host publishは途中飛ばし・並行実行・成果未確認を成功にせず、既存consumer互換のrole別finalだけを出力する。
- attempt/publish ownerが生存する限りleaseだけでownershipを奪わず、owner終了後の回収でも旧fenceからの更新を拒否する。
- protected path planとpublish段間Git factsはmain ledgerのtrusted入力・CAS証跡であり、task promptやaction引数を承認根拠にしない。
- owner planのbase digest、worktree content、index/commit tree、GitHub PR factsの一つでも不一致ならcrash recoveryを成功にしない。
- 最終外部効果の`completed`とhandoff保存後の`finalized`を分離し、その間のcrashでも外部操作を重複実行しない。
- reservation/completedへ束縛したcanonical handoff/final intent digestと異なるpayloadからfinalを確定しない。
