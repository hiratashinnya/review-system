# Codex Issue workspace durable binding 判断記録

Status: accepted（Issue #452）  
Date: 2026-08-26

## 問題と現行保証

Claude の `issue-implementer` / `issue-fixer` は Agent tool の `isolation: "worktree"`、
SubagentStart/Stop、ownership ledger、collect/release により `.claude/worktrees/agent-*` へ束縛される。
Codex は `collaboration.spawn_agent` に isolation 引数がなく、従来 implementer は平文 task name と
spawn 時 cwd/origin だけを検証し、fixer transport は manifest に存在しなかった。専用 worktree、branch、
expected OID、handoff、round、task の再利用禁止は暗号化 message 内の運用情報に留まり、agent 起動後の
command は別 cwd/origin/branch でも role 権限さえ合えば実行できた。

権限面では既に `agent-command-gate.sh` が implementer/fixer の push 可・merge 不可、reviewer の
push/自己修正不可を機械化している。この非対称と Claude isolation lifecycle は変更しない。

## 採用方式

主文脈が agent 起動前に、main worktree の `tmp/_worktree/ledger.json` へ次を `platform: codex` の
`open` entry として記録する。

- Issue、round、repository、専用 workspace、branch、expected OID
- role、handoff_path、平文 task key
- prepared_at、expires_at、agent_id/collected_to を含む ownership lifecycle

task key は implementer が `issue_<N>`、fixer が `issue_<N>_fix_r<R>` の canonical form とする。
prepare は workspace が main 配下の `.worktrees/<1要素>` であり、`git worktree list --porcelain` に
登録済みで、origin/branch/HEAD が指定値と完全一致する場合だけ成功する。同一 task key は終端後も再利用を
拒否し、同一 workspace の非終端 ownership 重複も拒否する。

spawn PreToolUse は tool name/role/task key と未期限・未消費の entry を一意に照合し、Git facts を再検証して
`running` へ一度だけ遷移する。Codex fixer は Claude と同じ `isolation_only` 区分に Codex transport を持ち、
blocker API を再実行せず既存の karte diagnose → fix → test → commit → push → handoff 契約へ入る。

全 tool の PreToolUse は top-level role と payload cwd を active entry へ照合し、origin/branch/worktree登録を
再確認する。HEAD は spawn 時には expected OID と完全一致を要求し、起動後は agent 自身の正当な commit を
許すため expected OID の descendant のみ許可する。別 cwd、別 origin、別 branch、履歴を付け替えた OID、
欠落/重複/期限切れ binding は tool 実行前に fail-close する。

終了時は handoff を同じ相対 path で main worktree へ collect し、ledger を `collected`、その後 ownership を
`released` にする。`collected_to` は entry に残す。途中失敗では entry を削除せず open/running/stopped/
collected の非終端状態に残すため、主文脈が同じ task key で回収を再試行できる。

## 却下案

- 暗号化 message の復号・解析: hook が信頼できる平文として観測できず、transport 実装にも依存する。
- task name と cwd だけの都度導出: round/handoff/branch/OID/ownership と task 再利用を証明できない。
- 環境変数や一時的な親プロセス状態: durable でなく、agent command から同じ値を検証できない。
- fixer を worker/implementer として起動: karte の書き手、push/merge、レビューと修正の役割分離を壊す。
- Codex 用に Claude ledger/lifecycle を置換: 稼働済み isolation、SubagentStop、residue deny を退行させる。

## Security trade-off と限界

ledger は暗号学的署名ではなく、main worktree のファイル境界と hook を信頼境界にする。主文脈は prepare/
collect/release を実行できるが gated agent には当該 module を allowlist せず、自己 binding の作成・解放を
許さない。全 tool hook により Bash 以外の write tool も workspace 検証対象になる。

起動後の HEAD は expected OID の descendant を許容するため、同じ branch 上の外部 descendant commit は
区別しない。これは agent 自身の commit を PostToolUse なしで許すための最小緩和であり、origin/branch/cwd と
ownership の一致は毎回維持する。より強い commit ごとの OID 更新は将来 AgentRun identity が導入された時に
検討する。

## bootstrap PR の finding 方針

本機構を導入する PR 自身の独立レビューで finding が出た場合、未導入 Codex fixerを別roleへ偽装して
起動しない。finding と再確認方法を記録して STOP し、原則は本 PR merge 後の main から正規 fixer transport
を起動する。merge 前修正が不可避なら、オーナーが明示した bootstrap 処置として通常 fixer round と分離して
記録し、同じ reviewer 文脈を修正担当にしない。

## 後続影響確認

Issue #452 は本実装 merge だけでは close しない。merge 後の main から PR #448/#449/#451 を fresh readし、
head/finding/CI/native relation/base同期を再評価する。#448 の F-407-01 は新 fixer transport、#449 の
F-374-01 は clean/remediation 両経路の lifecycle evidence、#451 は #370 を close しない clean canary 条件を
影響マトリクスとして #445 から追跡可能にしてから close 判断する。
