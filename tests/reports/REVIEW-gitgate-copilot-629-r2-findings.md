### F-629-01
harm: real
harm_detail: Copilot 登録を使った clone で後続 Claude subagent の差分検出による worktree 束縛が ambiguous-running となり、既存の自動実行経路が利用できなくなる。
severity: major
scope: in
locus: [gitgate/base_copilot.py::register, gitgate/base_records.py::authorization_records, issue_start/worktree_ledger.py::resolve_worktree_for_agent]
summary: 旧実装の Copilot 認可と running dispatch の混同は専用 base_authorizations collection と authorized/revoked lifecycle への分離により是正された。
evidence: OID 8fa8f70c の全diffとcanonical writerを確認し、一時Git fixtureの登録/pending/committed/aborted、本物running拒否、dispatch更新時保存、再登録revoked、破損collection拒否を含む4仮説再確認ケースが1.071秒でOKだった。
expected: Copilot認可とoperation証跡を維持しながら、Claude dispatch がない場合の既存 worktree 差分束縛が Copilot entry の存在に左右されない。
recheck: python3 -m unittest -v tests.unit.test_base_copilot.CopilotIntegrationTests.test_claude_fallback_registered_pending_and_committed tests.unit.test_base_copilot.CopilotIntegrationTests.test_claude_fallback_after_abort tests.unit.test_base_copilot.CopilotIntegrationTests.test_reregistration_revokes_authorization_without_dispatch tests.unit.test_base_copilot.CopilotIntegrationTests.test_corrupt_authorization_collection_is_fail_closed
status: resolved
disposition: fix-here
