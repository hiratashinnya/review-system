# Managed Issue-start と branch-source gate

## 決定

Issue-start blocker policy と branch-source policy は、判定材料、実行時点、reason code が異なるため別々の interception point で評価する。Issue-start hook は dispatch 直前に #297 blocker だけを評価し、#317 branch-source は後続の `gitgate new-branch` が評価する。GitHub standard API と git のみを使うため追加課金はない。

Issue #317 の interception point は **A: `gitgate new-branch` を primary** とする。現在 HEAD を暗黙継承せず、fresh fetch 後の `origin/<default>` exact OID からだけ branch を作る。正当な stacked branch は `--base-pr N` を明示し、same-repository・OPEN PR・API の head SHA・fetch した PR ref OID がすべて一致した場合だけ許可する。API failure、closed/cross-repository PR、partial response、OID mismatch は fail-close する。

branch-source の GitHub API read は blocker gate と同じ共通 resolver を使い、`GH_TOKEN`、`GITHUB_TOKEN`、`gh auth token --hostname github.com` の順で資格情報を解決し、すべて失敗した場合だけ匿名 read を試す。default branch の repository read と stacked PR の fetch 前後の read は、同じ client と資格情報を使う。token は `Authorization` header にだけ設定し、ログ、evidence、例外へ出さない。rate-limit remaining が0の `403` と `429`/`5xx` は `API_UNAVAILABLE`、GitHub provenance（`X-GitHub-Request-Id`）を伴う `401`/`403` は `API_PERMISSION`、**provenance を欠く `401`/`403` と、HTTP 応答自体が得られない通信失敗（DNS/接続/tunnel/timeout）は `API_UNREACHABLE`**、不完全応答は `API_PARTIAL_RESPONSE` として branch 作成前に fail-close する。通信失敗の写像は blocker gate 側（`blocker_gate/github.py` の `UrlLibReadTransport._open`）と同一である——同じ「GitHub が判断していない」事象を、共通 resolver 経由か transport 例外経由かで別 reason にしない（Issue #345 F-345-07）。どの reason でも verdict は deny のままで、branch-source に snapshot fallback は無い。

push gate は本 PR の対象外である。primary gate 後に local history が書き換えられる残余リスクは残るため、push/PR/merge 前の差分検査を追加するなら別の policy/interception point として扱う。PR 作成時は harness ごとに経路が異なり、merge 直前は手戻りが最大なので primary にはしない。

## Managed Issue-start

`issue_start/managed-entrypoints-v2.json` が有効/利用不能transportのinventory正本である。Claude `Task` / runtime `Agent`だけをbinding transportとして宣言し、Codex entryは退役済みで置かない。Codex側にissue-start hookは登録されていない（`.codex/hooks.json` はBashの`agent-command-gate.sh`と`adr-notify.sh`だけ）。

manifest は加えて `isolation_only` 区分を持つ（Issue #354 PR-4）。稼働中の経路は `issue-pipeline` から `issue-fixer` への Claude `Task` / runtime `Agent` であり、**shape 検証・`required_isolation` の強制・軽量 marker `ISSUE_FIX_BINDING_V1=<JSON>`（exact 6 field＝`issue`/`round`/`branch_name`/`repository`/`expected_oid`/`handoff_path`）の検証だけを行い、blocker gate（GitHub API）は呼ばない**。是正ラウンドは既に開いた PR への処置で Issue の着手可否は初回実装の dispatch で判定済みであり、ラウンドごとに API を叩くと到達不能時にレビュー是正まで fail-close で止まるためである。marker を無検証にせず要求するのは、worktree 所有台帳へ `{issue, round, branch_name, handoff_path}` を正確に載せるため（FR-W4）と、`gitgate adopt-branch --repository OWNER/REPO --expected-oid` に渡す値の出所を dispatch 契約側へ固定するためである。同じ `agent_type` が `managed` と `isolation_only` の両方に載っていれば、どちらの契約で判定すべきか一意に決まらないので manifest の誤りとして fail-close する。

`Agent`はClaude transportのtool名であり、Codex transportとして扱わない。Codex issue-start hookの退役経緯と旧wrapperの保存先は[`.ai/rationale/issue-pipeline.md`](../../.ai/rationale/issue-pipeline.md)「Issue #603: Codex main-context 資産の退役」を参照する。

Codex 0.146.0 の`tool_input.message`が暗号化されることに加え、custom agent schemaにper-subagent workspace項目がなく親workspaceを継承するため、task name/cwd/prepare ledgerからchild workspaceを推測するparserは退役した。その後に正規経路としていたrepo supervisorもIssue #538で退役した。Codexは主文脈にしないため、Codexからimplementer/fixerをdispatchする経路は無い。現在の状態は[`docs/methods/codex-workspace-binding.md`](../methods/codex-workspace-binding.md)を正とする。

Claude Code 2.1.221 Pro の通常 trust 実 TUI では、`.claude/settings.json` の matcher `Task` が UI 表示 `issue-implementer(hook deny probe)` の実 Agent tool 呼出しを捕捉した一方、PreToolUse stdin の `tool_name` は `Agent` だった。`tool_input` は Claude 固有の `subagent_type` / `prompt` / `description` shape である。この実測差に対応して manifest の Claude transport だけが `Task` と `Agent` を exact 名として持つ。`Agent` は Codex transport の parser alias にはしない。parser は Claude transport で `subagent_type` と `prompt` を必須とし、Codex 固有の `agent_type` / `message` / `task_name` が混在すれば拒否するため、同名 alias を harness 間で無条件に受理しない。小文字化、prefix/suffix、類似名も拒否する。

初回ac-designerのClaude transportはdispatch prompt に厳格な `ISSUE_START_BINDING_V1=<JSON>` 行を1つだけ含める。V1 の7 field、marker の欠如/重複なし、unknown field なしという契約を維持する。branch/base field は Claude compatibility のため marker 内で検証するが、branch-source ALLOW の根拠にはせず、後続 `gitgate new-branch` が fresh に再検証する。

著作ロールとfixerのClaude transportは加えて `tool_input.isolation` が exact `"worktree"` であることを要求する（manifest の `required_isolation`・Issue #350）。著作ロールは「独立worktreeで著作する」契約だが、その分離は role 側では作れない——`gitgate` に worktree を作成・移動する verb は無く、`agent-command-gate` の層2 が `cd` を deny するため、worktree を作れても移動できない。分離を与えられるのは dispatch 側だけなので、欠落は `ISSUE_START_ISOLATION_NOT_WORKTREE` で dispatch 自体を deny する。この検査は blocker read（GitHub API）より前の shape 検証段で閉じるため、API を消費しない。deny reason には reason codeに加えてdetailを載せる。

PreToolUse hook は次を順に行う。

1. harness 別 transport で tool / agent type / entrypoint / repository / Issue の binding を検証する。
2. `blocker_gate` Issue mode を fresh read し、結果 contract と対象 identity を検証する。Issue #299 完了前は waiver provider を渡さない。fresh read が `ERROR` かつ `reasons` に `API_UNREACHABLE` を含み、**かつ node を1件も読めなかった**場合に限り、孤立ブランチ `blocker-snapshot` の snapshot へ fallback する（policy §3.3）。1 node でも読めた invocation は到達できているとみなして fallback せず ERROR のまま deny する。fallback は fetch の前に `origin` を canonical `OWNER/REPO` へ正規化して invocation の repository と一致することを要求し（Codex transport の origin 検証と同じ正規化）、不一致は `ISSUE_START_SNAPSHOT_ORIGIN_MISMATCH` で fail-close する。
3. blocker が ALLOW の場合だけ同じ dispatch を続行する。BLOCK/ERROR、unknown、API/permission/pagination/cycle/contract error は deny する。

evidence は blocker の `fetched_at`・reason・policy version と対象 binding を含む。branch-source evidence は含めない。ALLOW evidence は hook stderr（harness log）へ出し、deny は reason/policy version を PreToolUse response に含める。

## #371の工程別入口

policyは `issue-start/1.0` から `issue-start/2.0` へ、このPRで一度だけmajor更新する。
旧implementer初回callerはac-designer入口と必須phase binding・承認入力へ移行する必要があり、
旧呼出しと非互換である。role専用worktreeへのremote exact OID継承もこの版の必須契約とする。
是正中に検討したminor 1.1は未公開で、非互換変更を許す既存規定がないため区分を訂正した。
manifestのJSON形状は互換のため `managed-issue-entrypoints/2` を維持する。


初回managed roleはac-designer、後続isolation_onlyはchange-planner/test-writer/issue-implementerと
既存fixer、readonlyはissue-investigator/plan-reviewer/pr-reviewer/adviserとする。3区分のrole重複は拒否する。
native新8工程のavailabilityはavailableとし、必須入力・承認・受渡し照合でfail-closeする。
Codex新profileのlive実測は #652 で追跡し、origin/main pinによる未merge拒否は維持する。
fixerは既存の軽量bindingを維持する。旧implementerの初回markerで工程を迂回してはならない。

新工程は `ISSUE_PHASE_INPUT_V1={"binding_file":"...","approval_file":"..."}` を必須とし、
trusted callerの入力束縛と独立review receiptを照合する。後続著作者はさらに
`ISSUE_PHASE_BINDING_V1` のexact 6 fieldsとworktree isolationを要求する。
readonlyのdispatchはworktree所有台帳を起票せず、直接編集とpushも許可しない。
入力/approvalのschema、1a→1b→2a→2bの順、owner承認、専用worktreeへの同branch継承の停止条件は
[Claude issue-pipeline](../../.claude/skills/issue-pipeline/SKILL.md)を正とする。

worktree継承決定は [FBK-20261017-工程別worktreeへ同一branchを継承する](../../.ai/feedback/ledger/FBK-20261017-工程別worktreeへ同一branchを継承する.toml) を参照する。
後続作者は6field bindingに加え `ISSUE_PHASE_PREDECESSOR_V1` のentry IDと回収receipt sha256を渡す。
前roleの最新台帳owner・Issue/branch・released/closed_at・collected_to実bytesとremote exact OIDを照合する。
既存collect/releaseを省略しない。native availabilityは有効であり、Codex profile pinと実測責任は別に維持する。

## Hook parity と限界

- Claude dispatch: `.claude/settings.json` の PreToolUse(`Task|Agent`) → `.claude/hooks/issue-start-gate.sh` → `python3 -P -m issue_start.hook`（cwd＝検査作業面を `sys.path` に入れない）
- Claude の read-only 工程の直接編集: `.claude/settings.json` の PreToolUse(`Write|Edit|NotebookEdit`) → `.claude/hooks/phase-tool-gate.sh` → `python3 -P -m issue_start.phase_tool_gate`（同じく cwd のコードを import しない）
- Codex: issue-start hook は登録しない（Issue #603 で退役。上記「Managed Issue-start」参照）

project hook が trusted/enabled で実際に fired した managed operation だけが保護対象である。direct shell/API invocation、未知 harness、hook を無効化した環境は manifest の unmanaged 分類であり、保護済みとは主張しない。`/hooks` と harness log で registration・trust・fire を確認する。
