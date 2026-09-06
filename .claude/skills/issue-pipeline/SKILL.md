---
name: issue-pipeline
description: Orchestrate a batch of open GitHub Issues through implement→PR→review→merge→close, one Issue at a time. The main thread stays thin — it triages processing order, dispatches issue-implementer / pr-reviewer sub-agents (model tier via bloom-model-tier, risk-based reviewer model), exchanges decisions with the owner via AskUserQuestion (showing premises/tradeoffs first), and tracks progress. Use when issue handling should proceed end-to-end with governance. NOT for authoring doc-system-v2 nodes (use spec-pipeline / impl-design-pipeline).
---

> **共通本文（必読）**: [`.ai/skills/issue-pipeline/SKILL.md`](../../../.ai/skills/issue-pipeline/SKILL.md)。実行前に必ず読み、Claude Code 固有の起動・権限・hook 制約を追加適用する。

設計判断の根拠は [issue-pipeline の canonical rationale](../../../.ai/rationale/issue-pipeline.md) を参照してください。
Claude 固有の rationale pointer は [`.claude/rationale/issue-pipeline.md`](../../rationale/issue-pipeline.md) です。
worktree／handoff の回復手順は [issue-pipeline の troubleshooting](../../../.ai/troubleshooting/issue-pipeline.md) を必要なときだけ参照してください。

## Claude Code 固有の dispatch 契約

- 主文脈だけが `AskUserQuestion` を使い、順序・オーナー判断・先送り・スコープ拡張を担う。`issue-implementer`、`issue-fixer`、`pr-reviewer` は非対話で STOP 報告する。
- `.claude/hooks/issue-start-gate.sh`、`agent-command-gate.sh`、worktree／karte の hook が有効な managed path を使い、契約エラーは迂回せず fail-close する。
- 実装は `issue-implementer`、レビュー／マージは `pr-reviewer`、レビュー是正は `issue-fixer` に分ける。実装者は merge 不可、レビュー者は push 不可の機械ゲートを前提にする。
- `.claude/agents/*.md` の変更内容が同一セッションの dispatch に直ちに反映されるとは限らない。変更後の契約を前提にせず、各 dispatch の実際の STOP 理由・受理形状を観測して適用契約を確認する。

### `issue-implementer` dispatch（`ISSUE_START_BINDING_V1` marker ＋ `isolation: "worktree"`）

`Task`/`Agent` dispatch の `tool_input.prompt` に、次の marker 行をちょうど1つ含める。欠落・重複・値の不正はいずれも hook が dispatch そのものを deny する。

```
ISSUE_START_BINDING_V1={"entrypoint":"issue-pipeline","repository":"OWNER/REPO","issue":N,"branch_name":"BRANCH","base_ref":"DEFAULT","base_oid":"40-HEX","base_pr":null}
```

exact 7 field（過不足はどちらも拒否）：`entrypoint`（常にリテラル `"issue-pipeline"`）／`repository`（`OWNER/REPO` 正規化）／`issue`／`branch_name`／`base_ref`（既定ブランチ名）／`base_oid`（fresh fetch 済み exact 40 桁 hex）／`base_pr`（stacked branch のときだけ OPEN PR 番号、それ以外 `null`）。
`branch_name`/`base_ref`/`base_oid`/`base_pr` は後続の `python3 -m gitgate new-branch` へ渡す値と同じにする。同じ dispatch に `isolation: "worktree"`（`Task`/`Agent` のパラメータとして渡し、prompt 本文には書かない）を渡す。

`handoff_path` は主文脈が作業ツリールート相対で採番して渡す：
`tmp/_handoff/issue-implementer--issue-<N>[-<suffix>].yaml`。絶対パスは渡さない。同一 Issue の複数ラウンドは `<suffix>` で分ける。handoff 回収は troubleshooting の手順に従う。

### `issue-fixer` dispatch（`ISSUE_FIX_BINDING_V1` marker）

`issue-implementer` と同様、次の marker と `isolation: "worktree"` を欠く dispatch は hook が呼び出し自体を deny する。

```
ISSUE_FIX_BINDING_V1={"issue":N,"round":R,"branch_name":"BRANCH","repository":"OWNER/REPO","expected_oid":"40-HEX","handoff_path":"tmp/_handoff/issue-fixer--issue-N-fixR.yaml"}
```

exact 6 field：`issue`／`round`（1始まり単調増加）／`branch_name`（既に PR が開いているブランチ名）／`repository`（`gitgate adopt-branch --repository` に渡す値）／`expected_oid`（remote 先端 exact 40 桁 hex）／`handoff_path`。
`isolation_only` 区分では shape・isolation・marker だけを検証する。

- **メインワークツリーのブランチは切り替えない**。`issue-fixer` は自分の worktree で `python3 -m gitgate adopt-branch <branch> --repository <repository> --expected-oid <expected_oid>` を実行して PR ブランチを取得する。
- **レビュー結果を先にカルテへ取り込む**（dispatch 前）：`python3 -m karte ingest-review --issue <N> --round <R> --from <repo-root 配下のパス>`。これは主文脈が実行する。
- **カルテのパスは渡さない**。渡すのは `{issue, round}` だけで、`issue-fixer` は `python3 -m karte <verb> --issue <N> --round <R>` で触る。進行ポインタ `tmp/_karte/active.json` は `ingest-review` が更新する。
- `adopt-branch` が `BRANCH_ADOPT_ALREADY_CHECKED_OUT` で失敗した場合や worktree が残留した場合は、troubleshooting の回収手順を主文脈で行う。

## 重い作業は agy を積極利用（fail-close）

横断影響調査・参照/孤児調査・スクラッチ計算などの重い調査は `agy-delegate` へ回す。移譲前に必ず疎通チェックし、NG なら移譲せず主文脈が直接遂行する。正本への書き込み・確定著作・無検証コード採用は移譲しない。
