---
id: TD-issue-542-001
version: 2
condition: boundary
---
# Purpose

Verify the all-role merge denial, read-only command availability, removal of classifier hook paths, and owner-only blocker report behavior introduced for Issue #542.

# Preconditions

- Run from the issue worktree with project settings and `.codex/rules/default.rules` present.
- Codex native-policy checks use `codex execpolicy check`; they inspect commands without executing them.
- Blocker report tests use fake GitHub snapshots and make no network request.

# Steps and expected results

1. Parse Claude settings and exercise native deny patterns for direct CLI calls and global-option forms, plus the GitHub MCP merge tools. Shell-hook checks cover wrappers, GitHub REST merge methods, and inline/file-backed GraphQL mutation payloads across the main context and agent roles.
2. Evaluate direct Codex CLI calls with `codex execpolicy check`. Each direct merge prefix is forbidden, and read-only repository/API calls are not forbidden by native rules.
3. Run Claude and Codex command-hook tests for all-role global-option detection and read-only controls. The reviewer cannot merge or push; implementer/fixer push remains permitted by the existing role contract.
4. Inspect platform hook registration and retired package files. No classifier or pre/post PR merge hook path remains.
5. Evaluate stable, blocked, and changing blocker snapshots through the owner report API. Stable ALLOW requires repeated identical evidence; BLOCK and unstable evidence fail closed; reports never authorize or call a merge API.
6. Invoke the report CLI with a fake collector. It emits JSON and an owner-action summary without calling a merge API.

# Acceptance

The focused tests pass. Read-only `git -C … status`, `gh pr view`, `gh --repo … pr view`, and `gh api` GET/GraphQL reads pass the applicable native-rule and hook checks. `maintainability_lint check` reports zero violations, `asset_parity check` reports zero missing assets, and `python3 -m unittest discover -s tests/unit` completes with each environment failure and its baseline cause recorded.
