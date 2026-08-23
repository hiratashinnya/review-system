---
name: issue-pipeline
description: Orchestrate a batch of open GitHub Issues through implement→PR→review→merge→close, one Issue at a time. The main thread stays thin — it triages processing order, dispatches issue-implementer / pr-reviewer sub-agents (model tier via bloom-model-tier, risk-based reviewer model), exchanges decisions with the owner via AskUserQuestion (showing premises/tradeoffs first), and tracks progress. Use when issue handling should proceed end-to-end with governance. NOT for authoring doc-system-v2 nodes (use spec-pipeline / impl-design-pipeline).
---

> **共通本文（必読）**: [`.ai/skills/issue-pipeline/SKILL.md`](../../../.ai/skills/issue-pipeline/SKILL.md)。実行前に必ず読み、Claude Code 固有の起動・権限・hook 制約を追加適用する。

設計判断の根拠は [issue-pipeline の canonical rationale](../../../.ai/rationale/issue-pipeline.md) を参照してください。

## Claude Code 固有の dispatch 契約

- 主文脈だけが `AskUserQuestion` を使い、順序・オーナー判断・先送り・スコープ拡張を担う。`issue-implementer`、`issue-fixer`、`pr-reviewer` は非対話で STOP 報告する。
- `.claude/hooks/issue-start-gate.sh`、`agent-command-gate.sh`、worktree／karte の hook が有効な managed path を使い、契約エラーは迂回せず fail-close する。
- 実装は `issue-implementer`、レビュー／マージは `pr-reviewer`、レビュー是正は `issue-fixer` に分ける。実装者は merge 不可、レビュー者は push 不可の機械ゲートを前提にする。
- Claude 固有の rationale は `.claude/rationale/issue-pipeline.md` を参照するが、共有契約の正本は上記 `.ai` 本文である。
- `.claude/agents/*.md` の変更内容が同一セッションの dispatch に直ちに反映されるとは限らない。変更後の契約を前提にせず、各 dispatch の実際の STOP 理由・受理形状を観測して適用契約を確認する。

### `issue-implementer` dispatch（`ISSUE_START_BINDING_V1` marker ＋ `isolation: "worktree"`）

`Task`/`Agent` dispatch の `tool_input.prompt` に、次の marker 行をちょうど1つ含める。欠落・重複・値の
不正はいずれも hook が dispatch そのものを deny する（起動されない）。

```
ISSUE_START_BINDING_V1={"entrypoint":"issue-pipeline","repository":"OWNER/REPO","issue":N,"branch_name":"BRANCH","base_ref":"DEFAULT","base_oid":"40-HEX","base_pr":null}
```

exact 7 field（過不足はどちらも拒否）：`entrypoint`（常にリテラル `"issue-pipeline"`）／`repository`
（`OWNER/REPO` 正規化）／`issue`／`branch_name`／`base_ref`（既定ブランチ名）／`base_oid`（fresh fetch
済み exact 40 桁 hex）／`base_pr`（stacked branch のときだけ OPEN PR 番号、それ以外 `null`）。
`branch_name`/`base_ref`/`base_oid`/`base_pr` は後続の `python3 -m gitgate new-branch` へ渡す値と同じ
にする。同じ dispatch に `isolation: "worktree"`（`Task`/`Agent` の**パラメータ**として渡す。prompt 本文
ではない）を渡す——渡さなければ実装者は主文脈と working tree を共有してしまう。**この要求は
`issue-implementer` と `issue-fixer` の両方に掛かる**（後者は Issue #354 で追加）。他の subagent
（`pr-reviewer`・各 `*-author` 等）は unmanaged で素通しされるので不要。

`handoff_path` は主文脈が「作業ツリールート相対」で採番して渡す：
`tmp/_handoff/issue-implementer--issue-<N>[-<suffix>].yaml`。絶対パスは渡さない（isolated worktree の
外への Write をハーネスが拒否するため）。同一 Issue の複数ラウンドは `<suffix>` で分ける
（`<key>` 一意化＝Issue #278・#323）。

### 戻り値の回収は「回収済みファイルを読む」（worktree は自動解放される）

dispatch の戻りは `HANDOFF: <実装者/是正者が実際に書けた絶対パス>` ＋1行要約。この絶対パスは
isolated worktree 内部を指すが、**`SubagentStop` フックが同期的に `collect-worktree` を実行し、
成功時は worktree ごと削除する**——happy path ではこの絶対パスは主文脈が読もうとする時点で既に存在
しない。**この絶対パスは Read しない。**

回収済みの実体を読む手順：

1. `<main-worktree>/tmp/_worktree/ledger.json`（worktree 所有台帳）を Read する。
2. `agent_type`（`issue-implementer` または `issue-fixer`）と `branch_name`（この dispatch に渡した値）
   が一致する**最新エントリ**を特定する（1 Issue ずつ直列に回している前提で一意に定まる）。
3. そのエントリの `collected_to` を読む。値が入っていれば `<main-worktree>/<collected_to>`
   （`tmp/_handoff/collected/<entry-id>--<basename>`）を Read する——これが書かれた handoff の実体。
4. `collected_to` が `null`（`status` が `stopped`/`stale` のまま自動回収が完了していない）なら、
   `python3 -m gitgate collect-worktree --entry <entry-id>` を主文脈が実行してから 3 を再試行する。
   **`status` が `running` のままなら「保留」**（実装者/是正者が handoff を一度も書かずに終了した＝
   契約違反かクラッシュ・Issue #423）。この状態で `collect-worktree` は `WORKTREE_LIVE` で拒否される
   ——上記「入れ子 dispatch をさせない」節の後始末手順（`worktree-forget`→`worktree-release`）で
   片付ける。**`status` が既に `released` なのに `collected_to` が `null` のままならさらに別系統**
   ——`collect-worktree` は no-op になるので、worktree の実体（残っていれば）と対応する PR の有無を
   主文脈が直接確認する。

`status: stop`（曖昧・矛盾）なら `stop_reason` ごと主文脈で受けてオーナーへ（PR7）。

### `issue-fixer` dispatch（`ISSUE_FIX_BINDING_V1` marker・Issue #354 PR-4）

`issue-implementer` と同様、次の2つを欠く dispatch は hook が呼び出し自体を deny する。

```
ISSUE_FIX_BINDING_V1={"issue":N,"round":R,"branch_name":"BRANCH","repository":"OWNER/REPO","expected_oid":"40-HEX","handoff_path":"tmp/_handoff/issue-fixer--issue-N-fixR.yaml"}
```

exact 6 field：`issue`／`round`（1始まり単調増加）／`branch_name`（既に PR が開いているブランチ名）／
`repository`（`gitgate adopt-branch --repository` に渡る値）／`expected_oid`（そのブランチの remote
先端 exact 40 桁 hex・`adopt-branch --expected-oid` に渡る値）／`handoff_path`。加えて `isolation: "worktree"`。
**②-a との違いは GitHub API を叩かないことだけ**（`isolation_only` 区分は shape・isolation・marker だけを
検証する）。

- **メインワークツリーのブランチは切り替えない**（FR-W7）。`issue-fixer` は自分の worktree で
  `python3 -m gitgate adopt-branch <branch> --repository <repository> --expected-oid <expected_oid>`
  を実行して PR ブランチを取得する。主文脈が `git switch` する手順は無い。
- **レビュー結果を先にカルテへ取り込む**（`issue-fixer` を dispatch する前）：
  `python3 -m karte ingest-review --issue <N> --round <R> --from <repo-root 配下のパス>`。
  **`ingest-review` は主文脈が実行する**——是正当事者には許可されない（自分の指摘を `resolved`
  にできてしまうため）。
- **カルテのパスは渡さない**（K2）。渡すのは `{issue, round}` だけで、`issue-fixer` は
  `python3 -m karte <verb> --issue <N> --round <R>` でのみ触る。所在解決は `karte` CLI の
  `main_worktree_root()` が担う。進行ポインタ `tmp/_karte/active.json` は `ingest-review` が更新する。
- `adopt-branch` が `BRANCH_ADOPT_ALREADY_CHECKED_OUT` で失敗した報告を受けたら、先行 worktree の解放
  （下記コマンド）は主文脈が行う。

### worktree の解放（②-a／②-c 共通・自動化されている）

- **実装者/是正者の worktree は `SubagentStop` フックが自動で回収・解放する**（回収＝ハンドオフを
  `tmp/_handoff/collected/` へ退避してから解放する1操作。回収できなければ解放しない）。主文脈が
  手順として実行することは無い。
- **残留した場合**（フック未発火・回収失敗）は次の dispatch が `ISSUE_START_WORKTREE_RESIDUE` で
  deny される。deny 文言のコマンド（`python3 -m gitgate collect-worktree --entry <entry-id>`）を
  実行して解消する。台帳に紐づかない worktree は `ISSUE_START_WORKTREE_UNCLAIMED` で deny され、
  `python3 -m gitgate worktree-release <path> --force-uncollected --reason <text>` で解消する。
  どうしても回収できないものは `python3 -m gitgate worktree-forget --entry <entry-id> --reason <text>`
  が唯一の逃げ道（理由は必須）。
- **不変条件 INV-W**：`.claude/worktrees/agent-*` に存在してよいのは、現在 live もしくは回収処理中の
  dispatch が所有する worktree だけである。残留は「ディスク使用量」の問題ではなく、古い作業ツリーを
  次の dispatch が掴むと**結果の信頼性そのものが損なわれる**害である（実測事象＝Issue #354）。
  だから機構は「掃除の推奨」ではなく次 dispatch の deny として実装されている。

  > **Codex 版（`.agents/skills/issue-pipeline/SKILL.md`）には本項は不要**（Codex には isolation
  > 機構自体が無いため。詳細＝`.ai/rationale/issue-pipeline.md`）。

### `SubagentStart`/`SubagentStop` の配線（Issue #309・#354）

恒常契約は各エージェントの `.md`/`.ai/agents/*.md` に常設し、フックは**機械的に拒否できる境界**だけに
使う：

- `SubagentStart`（matcher `issue-fixer`）→ `.claude/hooks/subagent-karte-inject.sh`：カルテ手順を
  `additionalContext` として注入する。
- `SubagentStart`（matcher `issue-implementer|issue-fixer`）→ `.claude/hooks/subagent-worktree-bind.sh`：
  起動した dispatch の worktree を所有台帳へ束縛する。
- `SubagentStop`（matcher `issue-implementer|issue-fixer`）→ `.claude/hooks/subagent-stop-gate.sh`：
  ①`issue-fixer` が `karte check` を通していない停止を `{"decision":"block"}` で拒否し（判定不能も
  拒否側）、②通ったら**その dispatch 自身の handoff が worktree にあるときだけ**台帳を
  `running`→`stopped` へ進めて `collect-worktree` で回収・解放する。**block したら②へ進まない**
  （単一決定点）。フックは `git worktree remove` を直接呼ばない——実体を消してよいかの判断は
  `gitgate/worktree.py` に集約されている。
- **停止イベント＝終了とは限らない**（Issue #423）。②が回収の起点にするのは「自分の handoff
  （`<agent_type>--issue-<N>…yaml`）が1件ある」という観測だけで、**無ければ台帳を進めず `running` の
  まま保留する**。理由＝実装者/是正者が入れ子の `Task` 委譲を行うと同じ `agent_id` の停止イベントが
  委譲のたびに届き、「終了した」と「委譲待ちで一時停止しただけ」を payload からは区別できないため。
  保留を `stopped`/`stale` へ落とすとそれ自体が residue になり、**同じ dispatch 自身の次の委譲**まで
  `ISSUE_START_WORKTREE_RESIDUE` で deny される（#338 実装中に実測）。

### 実装者/是正者に入れ子 dispatch をさせない（ノード著作チェーンは主文脈が回す・Issue #423）

**`issue-implementer` / `issue-fixer` に、その内側から複数段の subagent 委譲をさせない。** 特に
`*-author` →`reconciliation-validator` →`reconciliation` のノード著作チェーンは、主文脈が直接
オーケストレーションする（`.claude/rules/05-skills-agents.md`「ノード著作の委譲ルール」の 2 段確定は
主文脈の仕事であって、実装者に丸投げする手順ではない）。

- **やること**：ノード著作（FND/Q/DD 起票を含む）が要る Issue は、実装 dispatch のスコープから外し、
  主文脈が `*-author`→`reconciliation-validator`→`reconciliation` を回してから／回した上で実装を
  dispatch する。実装者が「著作が必要だ」と気づいたら **STOP 報告**させ、主文脈が引き取る。
- **なぜ**（実害・#338 実測）：入れ子委譲のあいだ停止イベントが繰り返し届き、委譲先の handoff が実装者の
  worktree の `tmp/_handoff/` に溜まる。#423 の是正でこれらは「保留」「他人の成果物」として正しく
  扱われるが、**入れ子が深いほど回収の起点が読みにくくなり、失敗時の切り分けコストが主文脈へ跳ね返る**
  ことは変わらない。多段入れ子を避ければ、この経路の失敗自体が発生しない。
- **1段だけの委譲は禁止していない**（read-only 調査など）。禁じるのは**成果物を書く多段チェーン**。
- **保留のまま戻ってきた dispatch の後始末**：実装者/是正者が handoff を一度も書かずに終了すると台帳は
  `running` のまま残る（`ISSUE_START_WORKTREE_RESIDUE` にはならないので次の dispatch は止まらない）。
  主文脈が `<main-worktree>/tmp/_worktree/ledger.json` の当該エントリを確認し、
  `python3 -m gitgate worktree-forget --entry <entry-id> --reason <text>` →
  `python3 -m gitgate worktree-release <path> --force-uncollected --reason <text>` で片付ける。
  **`ledger.json` を直接編集しない**——`update_ledger` のロックを経由しない不安全な迂回になる
  （#338 対応時に3回行われた応急処置の再演を避ける）。

## 重い作業は agy を積極利用（fail-close）

横断影響調査・参照/孤児調査・スクラッチ計算などの重い調査は `agy-delegate` へ回す。移譲前に必ず疎通
チェックし、NG なら移譲せず主文脈が直接遂行する。正本への書き込み・確定著作・無検証コード採用は
移譲しない。
