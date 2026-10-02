---
id: TR-ISSUE-542-004-2fc4cfb
type: TR
version: 1
condition: failure
result: FAIL
log_ref: tests/logs/TR-ISSUE-542-004-2fc4cfb.txt
---
# Issue #542 Finding 4 — base commit reproduction

## Purpose

Check whether the four failures listed in the Issue #542 test run also occur at base commit `2fc4cfb`, using a separate detached worktree.

## Preconditions

- The base validation worktree was created from `2fc4cfb` and was clean.
- The focused `unittest discover` commands ran at the worktree root. No repository code or tests were edited in that worktree.

## Result

- Both rate-limit parser failures reproduced: the watcher returned `FALLBACK` instead of the expected `OK` record.
- The installed Codex profile test reproduced an error because the installed CLI reports three feature names absent from the supervisor's feature catalog: `daemon_auto_start`, `system_proxy_fallback`, and `unified_exec_tty`.
- The helper compile test passed on the clean base worktree. The earlier read-only `__pycache__` failure did not reproduce there; it is consistent with the prior run's read-only worktree environment, not with a change in Issue #542. The affected test and supervisor code are unchanged between `2fc4cfb` and the issue branch.
- No code was changed for these baseline/environment failures.

## Measurement

- Tested commit: `2fc4cfb`.
- Run date: 2026-10-02.
- Environment: Python 3.12; Codex CLI feature inventory from the installed local CLI.
- Complete focused output: `tests/logs/TR-ISSUE-542-004-2fc4cfb.txt`.
