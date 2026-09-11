---
name: issue-pipeline
description: 複数のオープン GitHub Issue を実装→PR→レビュー→マージ→クローズで1件ずつ処理するオーケストレータ。処置順の確定、issue-implementer/pr-reviewer サブエージェントへの委譲（model は bloom-model-tier、レビュー model はリスクベース）、オーナーとの意思決定、進捗管理を扱う。Issue 処理を end-to-end で進めるときに使う。doc-system-v2 ノード著作には使わない（spec-pipeline / impl-design-pipeline を使う）。
---

## 共通本文

この資産の共通本文は [issue-pipeline の共通本文](../../../.ai/skills/issue-pipeline/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Codex CLI 固有の dispatch 契約

- GitHub の Issue/PR 操作は connector-first とし、利用可能な GitHub connector/tool を先に使い、不足する機能だけ `gh` CLI で補う。
- `collaboration.spawn_agent` の Codex implementer/fixer transport は現行 `unavailable`。`spawn_agent` が child workspace を受け取れず、PreToolUse が各 tool の実効 workdir・actual agent identity・spawn 成功を trusted 値として運ばないため、今後もこの経路を保護済み dispatch として宣言しない。
- Codex implementer の task key は exact `issue_<Issue番号>`、fixer は exact `issue_<Issue番号>_fix_r<round>`。repo supervisorの`run`がowner指定launch specとlive Git factsを照合し、同じledger transactionでimmutable launch recordとattemptを予約する。prepare/TTL/refresh/collect/releaseは使わない。PID/start tokenとJSONL `thread.started`を観測してからactual threadを束縛する。
- 既存 issue-start hook が既知Codex implementer/fixer dispatchをpayload詳細より先に常時`ISSUE_START_TRANSPORT_UNAVAILABLE`でfail-closeする。manifestの`binding_transports.codex`とall-tool binding hookは退役済みであり、別roleへ偽装して迂回しない。
- supervisorはmain checkout/共通Gitをread-only、対象worktreeだけwriteable、private `/tmp`/`/dev`、Codex API control-plane通信を維持する。innerは`codex --profile issue-supervised --strict-config exec -C <worktree>`で起動し、profileがworkspace-write相当、approval never、data-plane network deny、multi-agent/apps disabledを設定する。literal `--sandbox`はprofileと併用せず、compatibility検査が`LEGACY_SANDBOX_PRESENT`で拒否する。full MCP broker、feature catalog束縛、Landlock EXECUTE allowlist、command毎fresh-bwrap、空procfs、CAS束縛MCPは使わない。role contract digest、durable session、protected patch、host publish CASは維持する。
- inner Codexは編集・test・role別schema v1 `pre_publish` handoffまで。commit/push/PRはexit後のhost側`publish` executorへ戻し、protected patch（宣言時のみ）→add→commit→push→implementer PR createの順序と段間HEAD/commit tree/index tree/worktree content/upstream factsをledger CASで強制し、role別final handoffをhost生成する。publish reservationはowner process identityとleaseを持ち、owner crash後だけ回収する。PR create回収はrepository/head/base/head OID/owner/open/non-draftが一意一致する既存PRだけを採用する。`run`/`resume`はowner process identity付きactive attempt reservationを取り、生存ownerはlease期限後もfenceし、resumeは最新の未消費rate-limit pauseだけを受け付ける。JSONL/exit/handoffのいずれかが不正なら非終端entryとworktreeを保持する。
- dispatch deny・process failure・local `thread.started`だけを成功証拠にしない。`turn.completed`、exit 0、実handoffの実装後観測を揃える。
- 実装担当は `.codex/agents/issue-implementer.toml`、是正担当は `.codex/agents/issue-fixer.toml`、レビュー担当は `.codex/agents/pr-reviewer.toml` の developer_instructions にある恒常契約を適用する。implementer/fixer は push 可・merge 不可、reviewer は自己修正/push 不可という hook 機械ゲートを維持する。
- この binding 機構を導入する bootstrap PR 自身に finding が出た場合、未導入の Codex fixerを worker・implementer・別roleへ偽装して迂回しない。bootstrap PR は独立 reviewer の finding を記録して STOP し、runtime 観測が揃うまで正規 Codex fixer を予定しない。オーナーが明示した bootstrap 処置だけを role 偽装と分離した記録で行う。
- 実装の model／effort は Bloom ルーブリック、初回レビューの effort は共通本文のリスク信号で選ぶ。再レビューは既定 `high`、レート制限を理由に降格しない。
