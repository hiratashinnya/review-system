---
name: silent-failure-diagnosis
description: Diagnose an external process (delegated CLI/agent, hook, CI job, external service) that ends with a success signal (exit 0, status SUCCESS, Overall OK) but whose result is wrong, stale, empty, truncated, or silently permission-denied — check hard blocks first, verify it read the intended input, read side channels past aggregate success signals, reproduce before attributing cause, compare versions and mtimes, mine persistent logs for the regression boundary, identify the production launch path, and prefer least privilege. Shared reference intended to be preloaded by delegation agents via the skills frontmatter field (agy-delegate preloads it via Claude skills; Codex reads the shared body explicitly; production execution awaits verified runtime contracts). NOT spec/design inspection (spec-inspector), NOT asset audit (asset-auditor), NOT product test design (test-strategy), NOT the tool-specific symptoms or recovery steps of a delegate (agy-delegate / codex-review own those).
user-invocable: false
---

この Skill の共通本文は [`.ai/skills/silent-failure-diagnosis/SKILL.md`](../../../.ai/skills/silent-failure-diagnosis/SKILL.md) にあります。作業時は必ず共通本文を読み、その内容を適用してください。
