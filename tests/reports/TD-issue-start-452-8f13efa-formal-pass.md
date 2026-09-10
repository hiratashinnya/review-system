---
id: TD-issue-start-452
version: 6
condition: normal
result: PASS
log_ref: tests/logs/TD-issue-start-452-8f13efa-formal-pass.txt
---

# 目的

Issue #452改訂契約について、Codex spawn binding退役、supervisor direct-exec縮小、durable
recovery、権限非対称、model-originated commandのmodel/API到達遮断を検証する。旧brokerまたは
未実装時ログを成功証拠にしない。

# 前提

- Claude transportはmanifest marker/worktree isolationを維持する。
- Codex正規経路はIssue専用worktreeのrepo supervisorだけである。
- `run|resume`の親入力はIssue、role、change-plan ID、fixer roundだけである。
- host control-planeとmodel command data-planeは別境界である。

# 手順と期待結果

1. manifest、hook、module inventoryを検査する。
   - `binding_transports.codex`、`codex_binding.py`、`codex_exec_broker.py`、all-tool binding hookがない。
   - Claude transportと既存3つのPreToolUse groupが維持される。
2. `spawn_agent`/`collaborationspawn_agent`でimplementer/fixerを指定し、正常・欠落・混在payloadを与える。
   - payload詳細、cwd、ledger、GitHub API評価前に全て`ISSUE_START_TRANSPORT_UNAVAILABLE`。
   - ledger/handoff/sessionへの副作用0。
3. issuer済みcanonical entryと4入力をsupervisorへ渡す。
   - control-plane issuerには登録済み専用worktree、capture済みIssue/karte、approver、protected path名だけを渡し、
     repository/branch/OID/task key/handoff/finding ID/digest/model/runtimeは導出される。
   - ledger pending→sources→ledger complete→planの各crash点でlaunchはfail-closeし、同一内容retryだけが同じentryを
     修復する。retry時もcanonical expectedを再導出し、保存digestだけでなくimmutable fieldを個別照合する。
     異内容、別ID、exact entryと併存するactive identity、active workspace衝突、concurrent issuer、tamperは拒否する。
   - issuer生成fixtureをruntime loaderへ通し、同じentryへのintent digest付きsupervisor attempt予約まで到達する。
   - root→main→tmpへtrusted owner/mode/NSS policy、control/sources/change-plansへcurrent-user 0700を要求し、
     world-writable non-sticky、foreign/NSS-unresolved group-writable ancestorを発行前に拒否する。
   - 検査済みdirfd identityを保持し、0600 unique temp O_EXCL/O_NOFOLLOW、file fsync、同一dirfd hard-link no-clobber、
     temp unlink、directory fsyncを行う。tmp/control/source directoryのrename/symlink swap、既存leaf collision、途中例外で
     canonical外へのsource/plan/temp生成や異内容上書きがなくfail-closeし、同一内容retryだけが修復する。
   - Issue snapshot v2はrepository/number/body/nonempty ACとcapture actor/UTC秒/method=`github-api`、karte snapshot v2は
     exact round/open findingsとcapture actor/UTC秒/method=`karte-cli`を検証する。v1、field欠落/追加、無効/未来時刻、
     自由文methodを拒否し、captureとapprovalのactor/timeを別記録としてretry後も保持する。
   - issuerはGitHub取得、worktree作成、model/API/Claude起動を行わず、owner approvalはactor/timeの運用記録である。
     capture metadataもtrusted host callerの運用記録であり、GitHub応答や本人性の暗号学的証明ではない。
   - 同じentry IDをimmutable intent digestとattemptで拡張し、第2entryを作らない。
   - 旧all-field/thread/prompt/config/executable/timeout入力、unknown/duplicate、identity不一致、二重attemptを拒否する。
   - TTL/refresh/prepared stateがない。
4. direct commandを構築する。
   - `codex exec -C <worktree>`、workspace-write相当、approval never、network deny、shell env none。
   - Issue #491で確認した派生6 featureと、0.153.4実catalogで追加観測したautomation/tool featureを
     明示的にfalseへ固定する。feature listは複数語maturityを含め先頭name・末尾stateで厳密に読み、
     catalog外で有効なprocess能力名はknown扱いへ自動追加せずfail-closeする。
   - MCP broker、feature catalog完全一致、Landlock EXECUTE allowlist、fresh-bwrap/command、空procfsがない。
5. fake auth、fake endpoint listener、fake installed Codex markerでmodel-free probeを行う。
   - 親listener positive control成功。
   - child network失敗、listener request 0。
   - auth env/path、Codex marker、継承FDがchildから利用不能。
   - 検証不能なCLI構成はmodel/API/thread開始前にfail-close。
6. fake JSONL/process runnerでrun/resume/crashを検証する。
   - PID/start-token→一意なthread.started→turn.completed→exit 0→handoffの順だけ成功。
   - malformed/duplicate/denied tool/timeout/nonzero/missing handoffは失敗entryを保持。
   - rate limitだけpausedになり、resume commandは返さずavailabilityだけ返す。
   - resume threadはlatest paused attemptとentry agent_idからlock内で導出し、親入力を拒否する。
7. Popen直前race matrixを検証する。
   - plan/manifest/Issue/karte/ledger/role/executable/Gitの各変更はPopen 0でfailed記録になる。
   - 全authority evidenceとgenerated profile/runtime/commandが不変の場合だけPopen 1になる。
   - final reservation/owner PID-start-token/intent digest/live Gitの検査からprocess-start記録まで同一ledger
     lockを保持し、同期cooperative writerはcallback前に進まず、記録直後に進む。
   - lock FDはCLOEXECで、Popen/callback/ledger commit例外でも解放され、model実行中は保持しない。
8. protected patchとpublish state machineを検証する。
   - owner exact path/base digest、atomic replace、段間content/HEAD/index/upstream CASを強制。
   - implementer/fixerはpush可merge不可。implementerだけPR create可。reviewerは自己修正/push不可。
9. 実装後の差分を含むcheckoutでunit/full coverageを実行し、handoffへ結果を記録する。
   - bootstrap-waiverがcommitを禁止する間はhistorical `tests/reports`/`tests/logs`を変更せず、
     commit後の恒久TRはhost publish後に別途作成する。

# 残余リスク

nested Codexがmodel到達失敗前にlocal thread recordを作る可能性は受容する。ただし成功証拠に数えず、
listener request 0と到達失敗を証拠とする。legacy `--sandbox workspace-write`とpermission profileの
非合成によりread denyを証明できない構成はAC達成扱いにしない。
PreToolUseはexact launchの早期guardrailであり、任意のdirect Codex shell wrapperを完全封鎖しない。
same-UIDの非協調host processによるprivate control state外乱は既存threat boundary外とする。

## 実測

- ヘッダ: TD version 6 / implementation commit `8f13efa1372301417de46f642161e07ff8c682ea` / prompt template version: N/A（model/API/Claudeを起動しない実行基盤テストであり、production prompt templateを入力しない） / baseline content hash: N/A（S6基準コンテンツを入力とするテストではない） / 2026-09-10 23:57:27–23:59:55 JST / Linux 6.18.33.2-microsoft-standard-WSL2 x86_64, host Python 3.12.3
- 実行コマンド: `rtk uv run --with coverage coverage run -m unittest discover -s tests -p 'test_*.py'`
- ログ: `tests/logs/TD-issue-start-452-8f13efa-formal-pass.txt`
- 結果: `1789 tests`、`OK (skipped=10)`、実行時間 `146.934s`、script footer `COMMAND_EXIT_CODE="0"`。
- coverage: 主文脈が実行した`rtk uv run --with coverage coverage report`でTOTAL `9007` statements / `1391` missing / `85%`を確認し、HTMLレポートを`htmlcov/index.html`へ生成した。`.coverage`と`htmlcov/`は生成物としてcommit対象外。
- warning: coverage.pyが`docidx`について`module-not-imported`を1件報告した。テスト本体はexit 0でPASSしており、coverage集計は生成済みである。
- 証拠同一性: TD SHA-256 `1165c2b2709c7a93ba43e9af6ba2b925ccd93023c4f1042c02915f3c6a0ffca3`、Git正規化後ログ SHA-256 `d99b09be9d49ae894fc6a14b717287779be9d3495b70d6762f304db80f1339b2`。
- 証拠区分: 本TRは実装commit `8f13efa`に対するpost-sync正式full-suite PASS証拠である。既存のFAIL/PASS TR/logは履歴として保持し、転用・上書きしていない。
