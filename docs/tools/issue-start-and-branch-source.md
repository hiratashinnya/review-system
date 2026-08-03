# Managed Issue-start と branch-source gate

## 決定

Issue-start blocker policy と branch-source policy は、判定材料と reason code が異なるため内部 policy を分離し、managed dispatch adapter で ALLOW を結合する。GitHub standard API と git のみを使うため追加課金はない。

Issue #317 の interception point は **A: `gitgate new-branch` を primary** とする。現在 HEAD を暗黙継承せず、fresh fetch 後の `origin/<default>` exact OID からだけ branch を作る。正当な stacked branch は `--base-pr N` を明示し、same-repository・OPEN PR・API の head SHA・fetch した PR ref OID がすべて一致した場合だけ許可する。API failure、closed/cross-repository PR、partial response、OID mismatch は fail-close する。

push gate は本 PR の対象外である。primary gate 後に local history が書き換えられる残余リスクは残るため、push/PR/merge 前の差分検査を追加するなら別の policy/interception point として扱う。PR 作成時は harness ごとに経路が異なり、merge 直前は手戻りが最大なので primary にはしない。

## Managed Issue-start

`issue_start/managed-entrypoints-v1.json` が保護対象の inventory 正本である。現時点では `issue-pipeline` から `issue-implementer` への Codex `spawn_agent` と Claude `Task` を managed とする。dispatch prompt には厳格な `ISSUE_START_BINDING_V1=<JSON>` 行を1つだけ含める。

PreToolUse hook は次を順に行う。

1. tool / entrypoint / repository / Issue / branch / base の binding を検証する。
2. `blocker_gate` Issue mode を fresh read し、結果 contract と対象 identity を検証する。Issue #299 完了前は waiver provider を渡さない。
3. blocker ALLOW 後だけ branch-source policy を fresh read/fetch し、exact base OID を検証する。
4. 両 policy が ALLOW の場合だけ同じ dispatch を続行する。BLOCK/ERROR、unknown、API/permission/pagination/cycle/contract error は deny する。

evidence は blocker の `fetched_at`・reason・policy version、対象 binding、branch-source policy version と OID を含む。ALLOW evidence は hook stderr（harness log）へ出し、deny は reason/policy version を PreToolUse response に含める。

## Hook parity と限界

- Codex: `.codex/hooks.json` → `.codex/hooks/issue-start-gate.sh`
- Claude: `.claude/settings.json` → `.claude/hooks/issue-start-gate.sh`
- 共通 core: `python3 -m issue_start.hook`

project hook が trusted/enabled で実際に fired した managed operation だけが保護対象である。direct shell/API invocation、未知 harness、hook を無効化した環境は manifest の unmanaged 分類であり、保護済みとは主張しない。`/hooks` と harness log で registration・trust・fire を確認する。
