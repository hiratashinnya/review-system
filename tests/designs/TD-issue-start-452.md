---
id: TD-issue-start-452
version: 3
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
    `/dev/urandom`だけをread-only bindし、device write範囲を追加しないこともcommand契約で確認する。
11. protected patchはowner-approved exact path、schema、base SHA-256、path traversal/symlink/sizeをhostが
    検証し、apply直前にもdigestを再確認することを確認する。

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
