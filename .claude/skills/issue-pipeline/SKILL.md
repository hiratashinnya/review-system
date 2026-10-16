---
name: issue-pipeline
description: Orchestrate GitHub Issues through investigation, verification design, solution planning, Red tests, implementation and independent phase reviews. The main thread dispatches separate contexts, records owner decisions and reports blockers for owner manual merge. NOT for authoring doc-system-v2 nodes (use spec-pipeline / impl-design-pipeline).
---

> **共通本文（必読）**: [`.ai/skills/issue-pipeline/SKILL.md`](../../../.ai/skills/issue-pipeline/SKILL.md)。実行前に必ず読み、Claude Code 固有の起動・権限・hook 制約を追加適用する。

設計判断の根拠は [issue-pipeline の canonical rationale](../../../.ai/rationale/issue-pipeline.md) を必要なときだけ参照する。
Claude 固有の rationale pointer は [`.claude/rationale/issue-pipeline.md`](../../rationale/issue-pipeline.md) である。
worktree／handoff の回復手順は [issue-pipeline の troubleshooting](../../../.ai/troubleshooting/issue-pipeline.md) を必要なときだけ参照する。

## Claude Code 固有の dispatch 契約

- 主文脈だけが `AskUserQuestion` を持ち、これを使ってオーナーの判断を仰ぐ。処置順の確定・先送り可否・スコープ拡張の起票要否・`scope` の覆し・`disposition` の決定はいずれもオーナーが決めるのであって主文脈が決めるのではない（`.ai/skills/issue-pipeline/SKILL.md`「役割分担」）。主文脈が担うのは原案の作成、`AskUserQuestion` での伺い、得られた決定の記録と実行である。`issue-implementer`、`issue-fixer`、`pr-reviewer` は `AskUserQuestion` を持たず、非対話で STOP 報告する。
- `.claude/hooks/issue-start-gate.sh`、`agent-command-gate.sh`、worktree／karte の hook が有効な managed path を使い、契約エラーは迂回せず fail-close する。
- 実装は `issue-implementer`、レビューは `pr-reviewer`、レビュー是正は `issue-fixer` に分ける。review が clean の場合も AI は fresh blocker report を作ってオーナーへ渡し、merge はオーナーが手動で行う。native deny は直接形の merge command prefix を拒否し、global option／wrapper／API／検査可能な間接実行は両 PF の共有 command hook が判定する。reviewer は push もできない。
- エージェント定義の変更後は、変更後の契約を前提にせず、各 dispatch の実際の STOP 理由・受理形状を観測して適用契約を確認する。

### `ac-designer` dispatch（`ISSUE_START_BINDING_V1` marker ＋ `isolation: "worktree"`）

`Task`/`Agent` dispatch の `tool_input.prompt` に、次の marker 行をちょうど1つ含める。欠落・重複・値の不正はいずれも hook が dispatch そのものを deny する。

```
ISSUE_START_BINDING_V1={"entrypoint":"issue-pipeline","repository":"OWNER/REPO","issue":N,"branch_name":"BRANCH","base_ref":"DEFAULT","base_oid":"40-HEX","base_pr":null}
```

exact 7 field（過不足はどちらも拒否）：`entrypoint`（常にリテラル `"issue-pipeline"`）／`repository`（`OWNER/REPO` 正規化）／`issue`／`branch_name`／`base_ref`（既定ブランチ名）／`base_oid`（fresh fetch 済み exact 40 桁 hex）／`base_pr`（stacked branch のときだけ OPEN PR 番号、それ以外 `null`）。
`branch_name`/`base_ref`/`base_oid`/`base_pr` は後続の `python3 -m gitgate new-branch` へ渡す値と同じにする。同じ dispatch に `isolation: "worktree"`（`Task`/`Agent` のパラメータとして渡し、prompt 本文には書かない）を渡す。

`handoff_path` は主文脈が作業ツリールート相対で採番して渡す：
`tmp/_handoff/ac-designer--issue-<N>[-<suffix>].yaml`。絶対パスは渡さない。同一 Issue の複数ラウンドは `<suffix>` で分ける。handoff 回収は troubleshooting の手順に従う。

### 工程の入力と独立レビュー束縛（全工程必須）

managedな初回1aにも、後続のphase dispatchにも、別行で次をちょうど1つ付ける。

```text
ISSUE_PHASE_INPUT_V1={"binding_file":"tmp/phase-input.json","approval_file":"tmp/phase-approval.json"}
```

bindingは信頼された主文脈が用意し、producer/Issue/run/target/入力digest/OIDとartifact実bytesのdigestを束縛する。
初回調査・1aはraw Issue snapshotとinvestigation起動/省略理由を束縛する。
approvalはrecipient/run_id/issue/target_key/snapshot_oid/context_id/owner_approved/reviewsを持ち、1bには1a、
2aには1a/1b、2bには1a/1b/2aの独立clean receiptを要求する。
各receiptはphase、reviewer、producer_context、review_context、artifact、artifact_digest、statusを持つ。
同じコンテキストの著作とレビュー、別run/Issue/target/snapshot、古い入力、digest不一致は拒否される。
review capture本体は #375 の責務であり、主文脈の期待値をreviewerの自己承認に置き換えない。

後続の著作ロール `change-planner` / `test-writer` / `issue-implementer` は、phase用の入口を使う。

```text
ISSUE_PHASE_BINDING_V1={"issue":N,"round":R,"branch_name":"BRANCH","repository":"OWNER/REPO","expected_oid":"40-HEX","handoff_path":"tmp/_handoff/<role>--issue-N-phase.yaml"}
```

exact 6 fieldsと `isolation: "worktree"` を維持する。handoffは本体artifactを含めず短い完了receiptとする。
read-onlyの `issue-investigator` / `plan-reviewer` / `pr-reviewer` / `adviser` は共有作業面を読み、
branch/handoff markerと所有台帳起票は持たないが、ISSUE_PHASE_INPUT_V1の入力・承認束縛は必須。
直接Write/Edit/NotebookEditも拒否し、出力の保存は信頼された呼び出し元のcapture経路を使う。
初回ac-designerだけがnew-branchを使い、著作者は自分の永続成果物をcommit/pushする。
同一worktree/adopt衝突のowner判断とロール別実行証跡が揃うまではmanifestのavailabilityをunavailableに保つ。
旧implementerへのmanaged新branch dispatchを使って工程を飛び越えてはならない。
STOP/availability拒否を生gitや別entrypointで迂回しない。

### `issue-fixer` dispatch（`ISSUE_FIX_BINDING_V1` marker）

`issue-implementer` と同様、次の marker と `isolation: "worktree"` を欠く dispatch は hook が呼び出し自体を deny する。

```
ISSUE_FIX_BINDING_V1={"issue":N,"round":R,"branch_name":"BRANCH","repository":"OWNER/REPO","expected_oid":"40-HEX","handoff_path":"tmp/_handoff/issue-fixer--issue-N-fixR.yaml"}
```

exact 6 field：`issue`／`round`（1始まり単調増加）／`branch_name`（既に PR が開いているブランチ名）／`repository`（`gitgate adopt-branch --repository` に渡す値）／`expected_oid`（remote 先端 exact 40 桁 hex）／`handoff_path`。
`isolation_only` 区分では shape・isolation・marker だけを検証する。

- **メインワークツリーのブランチは切り替えない**。`issue-fixer` は自分の worktree で `python3 -m gitgate adopt-branch <branch> --repository <repository> --expected-oid <expected_oid>` を実行して PR ブランチを取得する。
- **レビュー結果を先にカルテへ取り込む**（dispatch 前）：`python3 -m karte ingest-review --issue <N> --round <R> --from <repo-root 配下のパス>`。これは主文脈が実行する。
- **カルテのパスは渡さない**。渡すのは `{issue, round}` だけで、`issue-fixer` は `python3 -m karte <verb> --issue <N> --round <R>` で触る。
- `adopt-branch` が `BRANCH_ADOPT_ALREADY_CHECKED_OUT` で失敗した場合や worktree が残留した場合は、troubleshooting の回収手順を主文脈で行う。

### Codex 実行者経路（Claude Code 固有・Issue #538）

各工程ロールと既存 `issue-fixer` は、自分の linked worktree で元ロールの権限を維持してCodexへ実行を委譲できる。read-only roleは編集profileを使わない。経路は `python3 -m codex_worktree_exec`（`codex exec -C <worktree>` の薄いラッパー）だけで、契約は `docs/methods/codex-workspace-binding.md` を正とする。

- **使うかどうかとモデル・推論予算は主文脈が dispatch prompt に書く。** 例：`Codex 実行者: --model <モデル> --reasoning-effort <low|medium|high|xhigh|max>`。選定はリスク信号表に従い、Codex 側のモデル名と推論予算は `.ai/Individually-managed-lists.md`「Bloom の model mapping」の Codex 行で写像する。書かなければロールは従来どおり自分で実装・是正する。
- dispatch の marker・`isolation: "worktree"`・`handoff_path` の契約は変わらない。commit・pushは許可された著作ロール、PR作成はissue-implementerが行い、Codexは行わない。新ロールは `--binding-file` を指定する。`issue-fixer` は karte の診断を済ませてから起動する。
- **主文脈は自分でラッパーや `codex exec` を起動して実装・是正を代行しない。** 主文脈の起動は gate のロール専用層の対象外で機械では止められないため（設計の暫定決定 D7）、規律として守る。
- ロールがレートリミットやセッション上限で止まったら、Codex のモデル・推論予算も含めて同じ構成で再投入する。
- 実起動の検証設計は `tests/designs/TD-codex-worktree-exec-538-001.md`。TR とログは主文脈が検証専用環境で残す。

### karte 判定の直接通知（Claude Code 固有）

`karte ingest-review` / `karte close-attempt` の実行直後、通知機構が `karte status --json` の
判定を AI の出力を経由せずオーナーのチャットへ届ける。

- **発火対象**：`Bash` に加え、主文脈・`issue-implementer`・`issue-fixer`・`pr-reviewer`・
  `dsv2-lookup` に付与済みの `ctx_execute`／`ctx_batch_execute` 経由の
  `karte ingest-review` / `close-attempt` も同じ通知対象とする。
- **通知本文に含まれる内容**：未解消/直近解消の finding 一覧、verdict の3集合
  （`blocking_findings` ⊇ `blocking_harmful` ⊇ `undecided_disposition`）を常に含み、
  `escalate: yes` のときはその根拠（`stalled_findings`・`saturated_groups`）を含む。
- **fail-open**：判定不能・`karte status` 実行失敗・トリガー語を含まない stdin はいずれも
  無出力 exit 0 とする。詳細は `.claude/hooks/README.md`
  「karte-notify」節。

## agyの有効化条件

#606/#628とロール別制限の実測が揃うまで、工程ロールからagyへの通常委譲は無効とする。疎通成功だけで起動を許可しない。未検証の経路を成功扱いせず、roleの権限と承認点を維持できない場合はSTOPする。
