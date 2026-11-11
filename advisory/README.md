# Advisory central ledger (#782)

This is a separate canonical ledger from feedback_ledger (owner decisions) and
Karte (review/correction history). The ONLY persisted advisory record is a
single TOML file at .ai/advisory/ledger/ADV-YYYYMMDD-slugify(topic).toml.
Views, aging, and reconciliation are derived each time; no separate index.

The CLI uses the original doc-system-v2/slugify.py via
feedback_ledger/slugify_ref.py. An advisory has a concrete 1–30 character
immutable topic and ID. Records store sources (issue:782, pr:123,
finding:F-782-1), evidence, recommendation, triage rationale, versioned
policy, related IDs, disposition state, history, and linked existing Issue.

## Usage

Use a task branch and the actual target base ref. Example:

    export ADVISORY_CALLER_ROLE=main-thread
    python3 -m advisory new --base-ref origin/main --topic "見直す命名規則" \
      --created-on 2026-11-10 --source finding:F-782-1 \
      --evidence "Review artifact F-782-1" --recommendation "Clarify names" \
      --triage-rationale "harm:none; optional" --policy-version 1.0

    python3 -m advisory show --id ADV-20261110-見直す命名規則
    python3 -m advisory amend --base-ref origin/main --id ADV-... \
      --expected-sha256 <value-from-show> --reason "new evidence" \
      --evidence "Rechecked artifact"
    python3 -m advisory transition --base-ref origin/main --id ADV-... \
      --expected-sha256 <value-from-show> --reason "owner triage" --to triaged
    python3 -m advisory promote --base-ref origin/main --id ADV-... \
      --expected-sha256 <value-from-show> --reason "owner requested" \
      --existing-issue owner/repo#123
    python3 -m advisory list --today 2026-11-10 --stale-days 30
    python3 -m advisory check --against-ref origin/main --require-base

Exit codes: 0 success, 2 missing entry, 4 refused or invalid.

## Invariants and trust boundary

- All create/amend/transition/promote operations check caller role, take a
  process lock, compare the caller-supplied current SHA-256, validate the entire
  corpus, and replace one file atomically. They reject unsafe references.
- Every mutation is evidenced by a hash-linked, payload-bound history entry;
  UTC timestamps, actor attribution, and policy versions are schema checked;
  schema/version/state/ID and normalized ID/topic collisions are checked.
  A similar but genuinely distinct topic needs a recorded distinction reason.
  Meaning cannot be proven nonduplicative by string similarity alone.
- The base-ref must be a trusted, freshly fetched target branch, not a user
  controlled or stale local alias. PR CI checks the committed files against
  the current origin/main; an older base revision is an error. Git merge
  conflict resolution must not discard remote changes.
- Only an already existing GitHub Issue is linkable. The promote operation
  checks GitHub's API and rejects pull requests or unverified responses.
  It does not create Issues. It does not change the referenced Issue body.
- Reviewers and finding-triagers are read-only; they must not call write verbs
  or Write/Edit ledger files. The orchestrating main-thread alone performs
  verified writes. Instrument each harness with a deny rule for direct
  Write/Edit to .ai/advisory/ledger/** and a controlled main-thread CLI path.
- ADVISORY_CALLER_ROLE is NOT an authentication secret. A shell-capable
  attacker can spoof it, forge an entire audit chain, or bypass an in-process
  lock. The defense is layered: restricted agent tools, repository code
  review, base-comparison CI, and branch protection. No sandbox or signed
  provenance is claimed. External GitHub source existence is not checked
  during read-only lint; ledger related_ids and promoted Issue are checked
  as described.
- This issue does NOT change existing Karte clean decisions, triage auto
  application, reviewer authority, or STOP. That integration belongs to #785.
