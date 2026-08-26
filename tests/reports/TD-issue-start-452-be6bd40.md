---
id: TD-issue-start-452
version: 1
condition: boundary
result: PASS
log_ref: tests/logs/TD-issue-start-452-be6bd40.txt
---

# 目的

Codex issue-implementer/fixer が暗号化 message ではなく durable binding により専用 worktree へ束縛され、
既存 Claude isolation lifecycle と role 権限非対称を退行させないことを検証する。

# 前提

- main repository と `.worktrees/<name>` の実 linked worktree を一時領域に作る。
- origin、branch、expected OID、handoff、task key を既知値で固定する。
- wall clock は timezone-aware な固定日時を注入する。

# 手順

1. implementer binding を prepare し、spawn consume、全 tool command verify を実行する。
2. expected OID の descendant commit 後も verify できることを確認する。
3. handoff を collect して release し、ledger の status/collected_to を確認する。
4. fixer canonical task key を prepare し、`collaborationspawn_agent` transport から consume する。
5. 別cwd、別origin、別branch、stale OID、未登録worktree、欠落handoff、期限切れ、task再利用を個別に作る。
6. 全 tool hook が対象 role の binding 欠落を deny し、対象外 role を素通しすることを確認する。
7. 全 unittest、asset parity、既存 agent-command gate/Claude SubagentStop 回帰を実行する。

# 期待結果

- 正しい implementer/fixer は `open -> running -> collected -> released` へ進み、`collected_to` が残る。
- message 本文に binding が無くても task key と ledger から正規起動できる。
- 各不正条件は agent 起動または tool 実行前に固有 reason で fail-close する。
- 失敗 entry は削除されず回収可能な非終端状態に留まる。
- implementer/fixer push可・merge不可、reviewer自己修正不可、Claude isolation/collect/release/residue deny が維持される。

## 実測

- ヘッダ: TD version 1 / implementation commit `be6bd40` / prompt template N/A /
  criteria content_hash N/A / 2026-08-26 / Linux
- ログ: `tests/logs/TD-issue-start-452-be6bd40.txt`
- focused 189件、全 unittest 1,331件（skip 1）、asset parity missing 0 を確認した。
- 初回全実行の1失敗もログへ保持した。根本原因は新 Codex fixer transport に対する旧
  Claude-only asset assertion の更新漏れで、実装契約を両 transport の exact field 検証へ更新して解消した。
- coverage は環境に module が無く未実施。skill が自動導入を禁止するため、導入可否のオーナー判断待ち。
