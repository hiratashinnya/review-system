# Managed Issue-start と branch-source gate

## 決定

Issue-start blocker policy と branch-source policy は、判定材料、実行時点、reason code が異なるため別々の interception point で評価する。Issue-start hook は dispatch 直前に #297 blocker だけを評価し、#317 branch-source は後続の `gitgate new-branch` が評価する。GitHub standard API と git のみを使うため追加課金はない。

Issue #317 の interception point は **A: `gitgate new-branch` を primary** とする。現在 HEAD を暗黙継承せず、fresh fetch 後の `origin/<default>` exact OID からだけ branch を作る。正当な stacked branch は `--base-pr N` を明示し、same-repository・OPEN PR・API の head SHA・fetch した PR ref OID がすべて一致した場合だけ許可する。API failure、closed/cross-repository PR、partial response、OID mismatch は fail-close する。

push gate は本 PR の対象外である。primary gate 後に local history が書き換えられる残余リスクは残るため、push/PR/merge 前の差分検査を追加するなら別の policy/interception point として扱う。PR 作成時は harness ごとに経路が異なり、merge 直前は手戻りが最大なので primary にはしない。

## Managed Issue-start

`issue_start/managed-entrypoints-v1.json` が保護対象と harness 別 binding transport の inventory 正本である。現時点では `issue-pipeline` から `issue-implementer` への Codex `spawn_agent` と Claude `Task` / runtime `Agent` を managed とする。entrypoint、agent type、tool name、harness 固有の必須 field と混在禁止 field は manifest の exact value だけを受理し、欠如・不正・複数 transport に一致する曖昧な payload は fail-close する。

公式 Codex manual と CLI source は hook canonical 名を `spawn_agent`、matcher 互換 alias を `Agent` と定義している。一方、Codex CLI 0.146.0 の実 TUI で `collaboration.spawn_agent` を呼んだ PreToolUse stdin は `tool_name: "collaborationspawn_agent"` だった。この版差を閉じるため Codex matcher は3名だけを exact matchし、payload parser は manifest の canonical 名と実測名だけを managed dispatch として受理する。`Agent` は matcher alias であって stdin canonical 名ではないため parser alias にはせず、未観測の `collaboration.spawn_agent` 表記や類似 prefix/suffix 名も受理しない。

Codex 0.146.0 の `tool_input.message` は PreToolUse 時点で暗号化されるため、binding 材料に使わない。Codex transport は次の平文情報だけで束縛する。

1. `tool_input.task_name` が exact `^issue_([1-9][0-9]*)$` に一致し、capture した10進数を Issue 番号とする。先頭ゼロ、suffix/prefix、ハイフン形は受理しない。
2. top-level `cwd` と hook 実行 cwd の `realpath` が一致する。
3. その path が git worktree の top-level であることを `git rev-parse` で確認する。
4. `origin` を GitHub.com の HTTPS / SSH URL の厳格形式から canonical `OWNER/REPO` へ変換する。他 host、HTTP、credential 付き、複数行は拒否する。

Claude Code 2.1.221 Pro の通常 trust 実 TUI では、`.claude/settings.json` の matcher `Task` が UI 表示 `issue-implementer(hook deny probe)` の実 Agent tool 呼出しを捕捉した一方、PreToolUse stdin の `tool_name` は `Agent` だった。`tool_input` は Claude 固有の `subagent_type` / `prompt` / `description` shape である。この実測差に対応して manifest の Claude transport だけが `Task` と `Agent` を exact 名として持つ。`Agent` は Codex transport の parser alias にはしない。parser は Claude transport で `subagent_type` と `prompt` を必須とし、Codex 固有の `agent_type` / `message` / `task_name` が混在すれば拒否するため、同名 alias を harness 間で無条件に受理しない。小文字化、prefix/suffix、類似名も拒否する。

Claude transport は従来どおり dispatch prompt に厳格な `ISSUE_START_BINDING_V1=<JSON>` 行を1つだけ含める。V1 の7 field、marker の欠如/重複なし、unknown field なしという契約を維持する。branch/base field は Claude compatibility のため marker 内で検証するが、branch-source ALLOW の根拠にはせず、後続 `gitgate new-branch` が fresh に再検証する。

PreToolUse hook は次を順に行う。

1. harness 別 transport で tool / agent type / entrypoint / repository / Issue の binding を検証する。
2. `blocker_gate` Issue mode を fresh read し、結果 contract と対象 identity を検証する。Issue #299 完了前は waiver provider を渡さない。
3. blocker が ALLOW の場合だけ同じ dispatch を続行する。BLOCK/ERROR、unknown、API/permission/pagination/cycle/contract error は deny する。

evidence は blocker の `fetched_at`・reason・policy version と対象 binding を含む。branch-source evidence は含めない。ALLOW evidence は hook stderr（harness log）へ出し、deny は reason/policy version を PreToolUse response に含める。

## Hook parity と限界

- Codex: `.codex/hooks.json` → `.codex/hooks/issue-start-gate.sh`
- Claude: `.claude/settings.json` → `.claude/hooks/issue-start-gate.sh`
- 共通 core: `python3 -m issue_start.hook`

project hook が trusted/enabled で実際に fired した managed operation だけが保護対象である。direct shell/API invocation、未知 harness、hook を無効化した環境は manifest の unmanaged 分類であり、保護済みとは主張しない。`/hooks` と harness log で registration・trust・fire を確認する。
