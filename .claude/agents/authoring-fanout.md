---
name: authoring-fanout
description: Non-interactive orchestrator that fans out a BATCH of independent authoring targets to the per-type *-author agent selected by an `author` parameter (requirements-author | spec-author | analysis-author | design-author | verification-author), then runs reconciliation-validator once over the batch and hands VALIDATION_OK to reconciliation for write-back. Use ONLY when a pipeline skill has produced a list of multiple independent parent nodes each needing the same layer of authoring (VAL/SR/FR/NFR, SPEC, ACTOR/I/O/D/P/E/TERM, ORC/DS/MOD/PORT/PRS/SCM/CFG/PROMPT, or TD/TC/TR/VERIFY/FND/DD/Q/PEND). NOT for a single-node author task (call the target *-author directly). NOT a validator (it delegates to reconciliation-validator) and NOT itself the writer to main files (it delegates to reconciliation). Cannot ask the user — on any ROLLBACK, contradiction, or ambiguity it STOPs and reports to its caller.
tools: Task, Read, Grep, Glob, Bash
model: sonnet
skills:
  - spec-principles
---

## 共通本文

この資産の共通本文は [authoring-fanout の共通本文](../../.ai/agents/authoring-fanout.md) にあります。必ず読み、その指示に従ってください。
