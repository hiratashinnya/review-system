# Codex Issue workspace durable binding 判断記録

Status: fail-close degradation（Issue #452 review round 1）  
Date: 2026-08-27

## 問題と現行保証

Claude の `issue-implementer` / `issue-fixer` は Agent tool の `isolation: "worktree"`、
SubagentStart/Stop、ownership ledger、collect/release により `.claude/worktrees/agent-*` へ束縛される。
Codex は `collaboration.spawn_agent` に `cwd` / `workspace` / `isolation` 引数がない。
spawn の PreToolUse `cwd` は main-thread の turn/session cwd であり child cwd ではなく、
各 tool の PreToolUse も `exec_command.workdir` を含まない。さらに current payload は actual
agent identity と spawn 成功観測を信頼済み値として与えない。したがって次の4値は、
実 transport が提供するまで機械保証できない。

- child workspace
- 各 tool の実効 workspace
- actual agent identity
- spawn 成功

権限面では既に `agent-command-gate.sh` が implementer/fixer の push 可・merge 不可、reviewer の
push/自己修正不可を機械化している。この非対称と Claude isolation lifecycle は変更しない。

## 採用方式（fail-close 縮退）

主文脈が agent 起動前に、main worktree の `tmp/_worktree/ledger.json` へ次を `platform: codex` の
`open` entry として記録する。

- Issue、round、repository、専用 workspace、branch、expected OID
- role、handoff_path、平文 task key
- prepared_at、expires_at、agent_id/collected_to を含む ownership lifecycle

task key は implementer が `issue_<N>`、fixer が `issue_<N>_fix_r<R>` の canonical form とする。
prepare は workspace が main 配下の `.worktrees/<1要素>` であり、`git worktree list --porcelain` に
登録済みで、origin/branch/HEAD が指定値と完全一致する場合だけ `open` entry を作る。
この entry は「dispatch された」証拠ではなく、将来 transport 用の prepare-only 記録である。

manifest の Codex implementer/fixer transport は `availability: unavailable` とし、既存の
trusted issue-start PreToolUse hook が `ISSUE_START_TRANSPORT_UNAVAILABLE` で dispatch を拒否する。
新設 all-tool hook が未 trust で実行されなくても、dispatch 自体がこの既存 hook で止まる。

spawn 前の binding 検証は非破壊とし、`open -> running` には遷移させない。
residue deny、blocker deny、API failure、router failure の後も agent/handoff 不在の entry を
`running` に永久消費しない。TTL 内は同じ entry を再検証し、TTL を越えた `open` は同一 canonical
task・repository・workspace・branch・OID・handoff・role・roundの場合だけ、台帳ロック下で同じ entryを
新しいTTLへ原子的にrefreshする。旧prepared/expires時刻は `refresh_history` に残す。別identity、期限内の
二重prepare、running/terminal taskは従来どおりdenyする。

将来 transport を有効化するには、trusted start observer が
actual `agent_id` と workspace を同時に観測し、その identity を1度だけ `running` へ bind する。
各 command は role/workspace に加え `agent_id` 一致を必須とし、stale thread を
`CODEX_BINDING_AGENT_MISMATCH` で拒否する。

実 transport が上記観測を提供して有効化された後だけ、handoff の collect/release を使う。

## 却下案

- 暗号化 message の復号・解析: hook が信頼できる平文として観測できず、transport 実装にも依存する。
- task name と cwd だけの都度導出: round/handoff/branch/OID/ownership と task 再利用を証明できない。
- 環境変数や一時的な親プロセス状態: durable でなく、agent command から同じ値を検証できない。
- fixer を worker/implementer として起動: karte の書き手、push/merge、レビューと修正の役割分離を壊す。
- Codex 用に Claude ledger/lifecycle を置換: 稼働済み isolation、SubagentStop、residue deny を退行させる。

## Security trade-off と限界

ledger は暗号学的署名ではなく、main worktree のファイル境界と trusted hook を信頼境界にする。
しかし、信頼できるのは payload が実際に運ぶ値だけであり、task key を agent identity の代用にしたり、
turn cwd を effective tool cwd の代用にしたりしない。この制約による dispatch 不可は、
誤った保証を発効させるより安全な縮退である。

## bootstrap PR の finding 方針

本機構を導入する PR 自身の独立レビューで finding が出た場合、未導入 Codex fixerを別roleへ偽装して
起動しない。現行runtimeはmerge後も unavailable であり、trusted observation が追加されるまでは正規
Codex fixer transportを起動できるとは宣言しない。finding と再確認方法を記録してSTOPし、merge前修正が
不可避な場合だけ、オーナーが明示したbootstrap処置として通常worker fallbackを別記録にする。同じreviewer
文脈を修正担当にせず、この例外を正規fixer起動またはtransport保証の証拠として扱わない。

## 後続影響確認

Issue #452 は本実装 merge だけでは close しない。merge 後の main から PR #448/#449/#451 を fresh readし、
head/finding/CI/native relation/base同期を再評価する。#448 の F-407-01 は新 fixer transport、#449 の
F-374-01 は clean/remediation 両経路の lifecycle evidence、#451 は #370 を close しない clean canary 条件を
影響マトリクスとして #445 から追跡可能にしてから close 判断する。
