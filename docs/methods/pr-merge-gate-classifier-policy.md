---
policy_version: "1.18"
status: retired
authority: issue-542
---

# PR merge classifier policy — retired

This policy no longer describes a live classifier. Issue #542 removed the classifier, its pre-use and post-use hooks, and the hook wrappers. The final classifier contract (`classifier_version: 1.17`) is preserved in [`docs/archive/pr-merge-gate-classifier-policy-v1.17.md`](../archive/pr-merge-gate-classifier-policy-v1.17.md).

`policy_version: 1.18` versions this retirement notice; it does not identify a classifier implementation. The current merge permission boundary and owner-facing report procedure are documented in [`docs/tools/pr-merge-gate.md`](../tools/pr-merge-gate.md).
