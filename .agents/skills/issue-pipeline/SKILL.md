---
name: issue-pipeline
description: 複数のオープン GitHub Issue を実装→PR→レビュー→マージ→クローズで1件ずつ処理するオーケストレータ。処置順の確定、issue-implementer/pr-reviewer サブエージェントへの委譲（model は bloom-model-tier、レビュー model はリスクベース）、オーナーとの意思決定、進捗管理を扱う。Issue 処理を end-to-end で進めるときに使う。doc-system-v2 ノード著作には使わない（spec-pipeline / impl-design-pipeline を使う）。
---

## 共通本文

この資産の共通本文は [issue-pipeline の共通本文](../../../.ai/skills/issue-pipeline/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Codex CLI 固有の dispatch 契約

- GitHub の Issue/PR 操作は connector-first とし、利用可能な GitHub connector/tool を先に使い、不足する機能だけ `gh` CLI で補う。
- `collaboration.spawn_agent` の Codex implementer/fixer transport は現行 `unavailable`。`spawn_agent` が child workspace を受け取れず、PreToolUse が各 tool の実効 workdir・actual agent identity・spawn 成功を trusted 値として運ばないため、今後もこの経路を保護済み dispatch として宣言しない。
- Codex implementer の reserved task key は exact `issue_<Issue番号>`、fixer は exact `issue_<Issue番号>_fix_r<round>`。repo supervisorがこのkeyのprepared bindingを検証し、Issue専用worktreeで別`codex exec` processを起動する。task keyをagent identityの代用にはせず、OS PID/start tokenとJSONL `thread.started`を観測してから`running`へ束縛する。
- 既存 index の issue-start hook が `ISSUE_START_TRANSPORT_UNAVAILABLE` で Codex implementer/fixer dispatch を fail-close する。all-tool binding hook の未 trust を理由に別 role・unmanaged worker・direct shell へ迂回しない。turn/session `cwd` を child/effective workspace、task key を agent identity とみなさない。
- `prepare` は単独ではdispatch成功を意味しない。supervisor start前の照合で`open -> running`をconsumeせず、外側bubblewrap起動後にPID/start tokenと同一processのactual thread/workspaceを観測したときだけ1度束縛する。
- supervisorは外側でmain checkout/共通Gitをread-only、対象worktreeだけwriteable、`/tmp` privateとし、Codex API control-plane通信を維持する。内側Codexで`workspace-write`、approval never、web search/shell data-plane network/multi-agent/apps disabled、指定model/reasoningを固定する。role contractはhost mainのwrapper+common digestと対象branchの一致を起動前に検査し、clean hostでもtask専用durable sessionsだけを書込mountする。`.git`/`.codex`/`.agents`はread-onlyで、変更提案はbinding prepare時にmain ledgerへownerが記録したexact pathとbase SHA-256をhost検証するstructured patchに限定する。publish CLIやpromptのpath/digest自己申告は承認に使わない。
- inner Codexは編集・test・role別schema v1 `pre_publish` handoffまで。commit/push/PRはexit後のhost側`publish` executorへ戻し、protected patch（宣言時のみ）→add→commit→push→implementer PR createの順序と段間HEAD/commit tree/index tree/worktree content/upstream factsをledger CASで強制し、role別final handoffをhost生成する。publish reservationはowner process identityとleaseを持ち、owner crash後だけ回収する。PR create回収はrepository/head/base/head OID/owner/open/non-draftが一意一致する既存PRだけを採用する。`run`/`resume`はowner process identity付きactive attempt reservationを取り、生存ownerはlease期限後もfenceし、resumeは最新の未消費rate-limit pauseだけを受け付ける。JSONL/exit/handoffのいずれかが不正なら非終端entryとworktreeを保持する。
- `collect` / `release` はtrusted startで`running`に束縛され、`turn.completed`、exit 0、実handoffをsupervisorが確認したentryに限る。dispatch deny・process failureで`open`/`running`のentryを回収済みと推測しない。
- 実装担当は `.codex/agents/issue-implementer.toml`、是正担当は `.codex/agents/issue-fixer.toml`、レビュー担当は `.codex/agents/pr-reviewer.toml` の developer_instructions にある恒常契約を適用する。implementer/fixer は push 可・merge 不可、reviewer は自己修正/push 不可という hook 機械ゲートを維持する。
- この binding 機構を導入する bootstrap PR 自身に finding が出た場合、未導入の Codex fixerを worker・implementer・別roleへ偽装して迂回しない。bootstrap PR は独立 reviewer の finding を記録して STOP し、runtime 観測が揃うまで正規 Codex fixer を予定しない。オーナーが明示した bootstrap 処置だけを role 偽装と分離した記録で行う。
- 実装の model／effort は Bloom ルーブリック、初回レビューの effort は共通本文のリスク信号で選ぶ。再レビューは既定 `high`、レート制限を理由に降格しない。
