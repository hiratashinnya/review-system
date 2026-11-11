# Finding disposition policy v1.0 — Issue #781

## Boundary and ownership

- Policy SoT: `.ai/guidance/triage-policy-v1.json`; format metadata: `.ai/schema/triage-policy-v1.json`.
- Harm classification SoT **only**: `.ai/skills/review-harm/SKILL.md`. Never duplicate harm categories here. A `harm:none` is not permission to discard a finding, and `scope:out` does not waive harm analysis.
- Reviewer fact record is immutable; triager (#783) generates separate, source-bound evidence. Its `reviewer_verified`, `evidence_complete` and `ac_relation_verified` inputs must be checked against original artifact, issue/round/run/digest/OID and AC/VD/CP by the trusted caller. A bare absence of changed source lines is **not** evidence of AC non-relevance.
- `suggest()` is read-only. It returns a candidate, not owner authorization. `evaluate()` is also read-only and never updates Karte, writes feedback, edits code or merges. Only a future **trusted adopter** (#784–#786) may act on an applicable result; no actor can mint a `waived` result or override reviewer scope.

## Decision table and precedence

1. Owner review takes precedence on missing/invalid evidence, unknown policy/version, policy-ref mismatch, reviewer conflict, request to override scope, high-risk or spec decisions, scope expansion, or contradiction (`harm:none` with required violation/regression).
2. `fix-here`: any confirmed AC, approved design, mandatory contract violation, or change-caused regression; only if no owner-judgment condition above. No scope deferral for these cases.
3. `deferred` candidate: pre-existing, unchanged, minor severity, no AC/design/contract/regression obstacle, no high-risk. Actual disposition additionally requires verified recipient Issue and the authorized #683 handoff. Until #786 this feature stays disabled.
4. `advisory` candidate: `harm:none`, optional improvement, no AC/design/contract/regression obstacle. Actual disposition additionally requires verified committed advisory SoT; #782 supplies it. An unverified registry reference never releases a gate.
5. Otherwise `owner-review`. A classification does not change `status:open` or make the PR clean.

`rules` is an ordered, human-reviewable machine table. Safety constraints enforced in the evaluator are conservative and cannot be relaxed by editing rule operands; edits still require policy versioning and explicit owner approval. `fix-here` does **not** grant edit permission, and `deferred` does **not** initiate issue creation or handoff.

## Approval, rollback, and trust boundary

The initial policy has `status:draft`, `auto_apply_enabled:false`, and all three feature flags false. It only produces suggestions. This Issue does **not** constitute owner approval. To enable a decision, an owner must explicitly approve the disposition, scope and policy version; the judgment must be stored in existing `feedback_ledger` as a verifiable `FBK-` entry. A **trusted CLI**, not an agent or unverified JSON claim, must check owner identity, feedback ledger entry, allowed dispositions/phases, exact policy ref and canonical SHA-256 policy digest and supply an approval record plus an independently implemented `verify_owner` callback to `evaluate()`. A missing, false, throwing or non-boolean callback result rejects activation.

The `verified_by_trusted_cli` field is a boundary **assertion**, not a cryptographic proof. Until the adopter implements and independently validates it, it MUST be treated as untrusted and no result may be automatically applied; disabling `auto_apply_enabled` returns to the previous owner-only workflow. Any policy/config change changes the digest and invalidates prior approval. No feedback entry is fabricated for this draft.

Only `review`/`remediation_review` may ever be enabled in v1. `planning` and older data are excluded; no inferred conversion. The independent reviewer, triager and main thread cannot grant themselves scope override, merge, write to feedback_ledger, or authorization. Any contradiction with the owner's prior decision is a stop and escalation, not silent reclassification.

## Follow-on integration contract

- #783: create separate verified triage artifact bound to source context; do not accept user-controlled `reviewer_verified` assertions as evidence.
- #784: suggest-only ingestion, keep reviewer artifact and triage artifact separate, no disposition or verdict change.
- #785: enable only owner-approved `fix-here`/`advisory` paths after ledger, STOP and Karte validation; require committed advisory evidence.
- #786: conditionally enable `deferred` only with #683 recipient verification and handoff; measure errors and implement rollback.
- Automated reviewer/triager decisions alone never authorize an action. The user remains the final merge authority.
