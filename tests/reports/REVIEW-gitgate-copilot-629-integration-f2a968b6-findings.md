> 注記（Issue #706）: 本記録が参照する `tests/unit/test_base_copilot.py`（および関連する `gitgate/base_copilot.py` 等）は Issue #706 で削除された。本記録は履歴として当時のまま保持する。

### F-629-01
harm: real
harm_detail: Copilot認可をdispatchのrunning entryとして保存すると、後続Claudeのworktree差分束縛がambiguous-runningとなり既存実行経路を利用できなくなる。
severity: major
scope: in
locus: [gitgate/base_copilot.py::register, gitgate/base_records.py::authorization_records, issue_start/worktree_ledger.py::resolve_worktree_for_agent]
summary: 認可を専用base_authorizationsとauthorized/revoked lifecycleへ分離した是正を維持している。
evidence: f2a968b6の全PR固有diff2372行とregister/authority/records/journal/既存atomic writer/fallback本文を確認し、認可はentriesへ追加されず通常writerも専用collectionを保存する。
expected: 認可とoperation証跡を保持し、Claude dispatchがない時の既存worktree差分束縛を妨げない。
recheck: tests.unit.test_base_copilotの登録/pending/committed/abortedのfallback、実running拒否、再登録revoked、dispatch更新保持、破損collection拒否の対象ケースと保存ログを照合する。
status: resolved
disposition: fix-here
