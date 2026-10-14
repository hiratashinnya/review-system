### F-629-01
harm: real
harm_detail: Copilot 登録を使った clone で後続 Claude subagent の差分検出による worktree 束縛が ambiguous-running となり、既存の自動実行経路が利用できなくなる。
severity: major
scope: in
locus: [gitgate/base_copilot.py:37, issue_start/worktree_ledger.py::resolve_worktree_for_agent]
summary: Copilot 認可を共有台帳の running dispatch として残すため、既存 Claude consumer が別 platform の認可を live Claude dispatch と誤認する。
evidence: 実 Copilot fixture で登録→start→continue が committed となっても entry.status は running、Claude候補1件と非一致agent_idで resolve_worktree_for_agent が (None, ambiguous-running) を返し、同entryをreleasedにした対照では候補/diffを返した。
expected: Copilot認可とoperation証跡を維持しながら、Claude dispatch がない場合の既存 worktree 差分束縛が Copilot entry の存在に左右されない。
recheck: 下記一時Git再現を実行し、Copilot登録中/pending中/committed後/aborted後のいずれでも単一Claude候補が既存条件どおりdiffで束縛され、実Claude running entryがある場合は拒否されることを確認する。
status: open
disposition: fix-here
