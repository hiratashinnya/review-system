---
id: TD-issue-542-001
version: 1
condition: boundary
---
# Purpose

Verify the all-role merge denial, removal of classifier hook paths, and owner-only blocker report behavior introduced for Issue #542.

# Preconditions

- Run from the issue worktree with project settings and `.codex/rules/default.rules` present.
- Codex native-policy checks use `codex execpolicy check`; they inspect commands without executing them.
- Blocker report tests use fake GitHub snapshots and make no network request.

# Steps and expected results

1. Parse Claude settings and exercise deny patterns for direct and RTK-wrapped CLI calls, REST merge routes, GraphQL calls, and MCP tools across the main context and three named roles. Every required entry is denied.
2. Evaluate direct and wrapped Codex commands with the native execpolicy checker, including REST and file-backed GraphQL API forms. Every required command returns `forbidden`, including when user rules also contain an allow rule.
3. Run Claude and Codex command-hook tests. The reviewer cannot merge or push; implementer/fixer push remains permitted by the existing role contract.
4. Inspect platform hook registration and retired package files. No classifier or pre/post PR merge hook path remains.
5. Evaluate stable, blocked, and changing blocker snapshots through the owner report API. Stable ALLOW requires repeated identical evidence; BLOCK and unstable evidence fail closed; reports never authorize or call a merge API.
6. Invoke the report CLI with a fake collector. It emits JSON and an owner-action summary without calling a merge API.

# Acceptance

The focused tests pass. `maintainability_lint check` reports zero violations, `asset_parity check` reports zero missing assets, and `python3 -m unittest discover -s tests/unit` passes or records each unrelated environment failure with its traceback and cause.
