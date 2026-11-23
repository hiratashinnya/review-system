# Finding disposition policy v1.1 — Issue #781

## Boundary and ownership

- Policy SoT: `.ai/guidance/triage-policy-v1.json`; format metadata: `.ai/schema/triage-policy-v1.json`.
- Harm classification SoT **only**: `.ai/skills/review-harm/SKILL.md`. Never duplicate harm categories here. A `harm:none` is not permission to discard a finding, and `scope:out` does not waive harm analysis.
- Reviewer fact record is immutable; triager (#783) generates separate, source-bound evidence. Its `reviewer_verified`, `evidence_complete` and `ac_relation_verified` inputs must be checked against original artifact, issue/round/run/digest/OID and AC/VD/CP by the trusted caller. A bare absence of changed source lines is **not** evidence of AC non-relevance.
- `suggest()` is read-only. It returns a candidate, not owner authorization. `evaluate()` is also read-only and never updates Karte, writes feedback, edits code or merges. Only a future **trusted adopter** (#784–#786) may act on an applicable result; no actor can mint a `waived` result or override reviewer scope.

## Decision table and precedence

1. Owner review takes precedence on missing/invalid evidence, unknown policy/version, policy-ref mismatch, reviewer conflict, request to override scope, spec decisions, scope expansion, or contradiction (`harm:none` with required violation/regression).
2. `fix-here`: any confirmed AC, approved design, mandatory contract violation, or change-caused regression; only if no owner-judgment condition above. `high_risk` does not block this outcome. No scope deferral for these cases.
3. `advisory` candidate: `harm:none`, optional improvement, no AC/design/contract/regression obstacle, no worsening, no high-risk. Evaluated before `deferred`, so a pre-existing minor finding that also meets these conditions becomes `advisory`. Actual disposition additionally requires verified committed advisory SoT; #782 supplies it. An unverified registry reference never releases a gate.
4. `deferred` candidate: pre-existing, unchanged, minor severity, no AC/design/contract/regression obstacle, no high-risk. The rule checks severity only and does not read `harm`; see "Version 1.1: `harm:none` pre-existing minor findings that are not optional" for the intended consequence. Actual disposition additionally requires verified recipient Issue and the authorized #683 handoff. Until #786 this feature stays disabled.
5. Otherwise `owner-review`. A classification does not change `status:open` or make the PR clean.

`rules` is an ordered, human-reviewable machine table; `suggest()` adopts the first rule that matches and passes its safety check. The order `fix-here`, `advisory`, `deferred` is fixed by `triage_policy.contract.OUTCOMES` and the schema `prefixItems`. Safety constraints enforced in the evaluator are conservative and cannot be relaxed by editing rule operands; edits still require policy versioning and explicit owner approval. `fix-here` does **not** grant edit permission, and `deferred` does **not** initiate issue creation or handoff.

## Version 1.1: `high_risk` scope (Issue #783, F-783-02)

Policy 1.0 checked `high_risk` in the owner-judgment pre-gate, before rule evaluation. A required AC, design or contract violation, or a regression, therefore became `owner-review` whenever the triager also judged it high risk. That contradicted #781 AC1, which sends these violations to `fix-here` and does not list risk as an `owner-review` condition. It also contradicted the 1.0 policy data, where only the `deferred` rule had `high_risk` as a condition. In the #852 measurement, the AC5 regression F-783-01 became `owner-review` this way. The owner judged the pre-gate a design error.

Version 1.1 removes `high_risk` from the pre-gate. It now only blocks the `deferred` and `advisory` candidates. The evaluator enforces this in its safety checks, and the advisory rule lists it in `all_false` as well. A high-risk finding with no required violation therefore still ends in `owner-review` (`no-safe-rule`). The criterion for setting `high_risk` is defined in `.ai/agents/finding-triager.md`.

## Version 1.1: `advisory` before `deferred` (Issue #783, F-783-04)

The rules were ordered `fix-here`, `deferred`, `advisory`, and the evaluator adopts the first matching rule. A `harm:none` optional improvement that was also pre-existing and minor therefore matched `deferred` first. In the #852 E04 measurement (head b2615085, policy 1.1) the finding F-783-04 (harm none, optional improvement, pre-existing, minor) became `rule:deferred` instead of the expected `advisory`. `deferred` needs a recipient Issue and handoff, so a finding with no harm was offered the heavier disposition and asked for an unnecessary recipient. The owner decided that a `harm:none` optional improvement (no AC/design/contract violation, no regression, no worsening, not high risk) is an `advisory` candidate ahead of `deferred`, and that `deferred` is for pre-existing minor findings whose harm is not `none`. The rule order is now `fix-here`, `advisory`, `deferred`. The `high_risk` entry in the advisory rule's `all_false` stays as it is.

The policy version stays at 1.1. This change belongs to the same unmerged PR (#816) that already moved the policy from 1.0 to 1.1, and a review fix inside one unmerged version transition does not bump the version again (`.ai/guidance/common.md`, 正本・実装規約). None of the allowed reasons for a further bump applies: the MINOR classification is still correct, no bump was missed, and the version literals across the policy, schemas and contract already agree. Because the rule order is part of the canonical policy bytes, the policy digest changes, so any approval bound to the earlier 1.1 digest would no longer verify; no approval exists for this draft.

## Version 1.1: `harm:none` pre-existing minor findings that are not optional (Issue #783, F-783-05)

A finding with `harm:none`, `preexisting`, `severity:minor` and `optional_improvement:false` (and no AC/design/contract/regression/worsening/high-risk flag) does not match the `advisory` rule, which requires `optional_improvement`. It reaches the `deferred` rule, whose only value condition is `severity:minor`, and `suggest()` returns `deferred` (`rule:deferred`). This is an intended design, decided by the owner (option b) in the review of F-783-05. It is not a rule gap, and neither the rules nor the evaluator change.

- Reason: `harm:none` alone does not make a finding an advisory item. Advisory is reserved for a finding the reviewer or triager explicitly judged to be an optional improvement. A pre-existing minor finding that nobody called optional is still something the owner may want to track, so the lighter, no-handoff path is not the default for it.
- The wording "pre-existing minor findings whose harm is not `none`" described the typical case that reaches `deferred`; it was never a machine condition. The machine condition is the rule table: `deferred` does not read `harm`. A `harm:none` finding still reaches `deferred` only when it is pre-existing, minor and not an optional improvement.
- The candidate is only a suggestion. Actual `deferred` still needs a verified recipient Issue and the authorized #683 handoff, and the feature stays disabled until #786. If the owner judges that this finding needs neither, the owner decides; no actor may reclassify it silently.
- `tests/unit/test_triage_policy.py::test_preexisting_no_harm_minor_not_optional_is_deferred` pins this expectation. Changing it requires a policy change with a version bump, not an edit of the test alone.

The policy version stays at 1.1. This is a clarification inside the same unmerged PR (#816) that already moved the policy from 1.0 to 1.1; the rules, schema and policy digest are unchanged, so no bump is made and no allowed reason for a further bump (`.ai/guidance/common.md`, 正本・実装規約) applies.

## Version 1.1: proposal phases separated from auto-apply phases (Issue #783, F-783-06)

One constant (`PHASES`, two values) both validated the finding `phase` and had to equal the policy `enabled_phases`, and `finding_triager/inputs.py` kept its own copy. Widening it to express the upper phases would have widened `enabled_phases`, and therefore the range an owner approval could authorise. `authorization.evaluate` also never read `enabled_phases`; only the approval `allowed_phases` bounded it, so a finding of a newly accepted phase could have reached `auto_applicable` on an approval record alone.

The owner decided that proposal mode must cover five phases while automatic application stays at the existing two. `triage_policy/phases.py` now holds `AUTO_PHASES` (`review`, `remediation_review`) and `PROPOSAL_PHASES` (those plus `verification_design`, `solution_planning`, `test_design`), together with one table mapping each phase to its reviewer role, reviewed artifact type and Karte envelope phase. `validate_finding`, the artifact schema `phase` and the policy input schema `finding_evidence.phase` accept the five phases. `validate_policy` and the policy schema `enabled_phases` still require exactly `AUTO_PHASES`. `evaluate` returns `owner-review` with `phase-not-auto-enabled` for any phase outside the policy `enabled_phases`, whatever the approval, flags and status, and `_approved` rejects an approval whose `allowed_phases` names a phase outside `enabled_phases`. An unknown phase is still rejected by `validate_finding`.

The policy version stays at 1.1, and the policy bytes, digest, `enabled_phases`, `status`, `auto_apply_enabled`, feature flags, rules, the approval schema `allowed_phases` enum and the artifact schema identifier `finding-triage/v1` are unchanged. Reason: the change only adds suggestion-only phases; it does not change what may be applied automatically. A bump would invalidate approvals bound to the 1.1 digest, and this unmerged PR (#816) already moved the policy from 1.0 to 1.1, so a further bump is not allowed (`.ai/guidance/common.md`, 正本・実装規約); none of its three reasons applies. The artifact schema widening is additive: older review/remediation_review artifacts still validate, and artifacts of the new phases fail an older validator, which is the intended fail-closed direction. Enabling automatic application for an upper phase needs a policy change and a version bump (#857).

`tests/unit/test_triage_phases.py` pins this: the policy file values and digest, the `enabled_phases` and `allowed_phases` schema values, consistency of the table with the schemas and with the existing reviewer-role tables, and the negative case that proposal-only phases never become auto-applicable.

## Approval, rollback, and trust boundary

The initial policy has `status:draft`, `auto_apply_enabled:false`, and all three feature flags false. It only produces suggestions. This Issue does **not** constitute owner approval. To enable a decision, an owner must explicitly approve the disposition, scope and policy version; the judgment must be stored in existing `feedback_ledger` as a verifiable `FBK-` entry. A **trusted CLI**, not an agent or unverified JSON claim, must check owner identity, feedback ledger entry, allowed dispositions/phases, exact policy ref and canonical SHA-256 policy digest and supply an approval record plus an independently implemented `verify_owner` callback to `evaluate()`. A missing, false, throwing or non-boolean callback result rejects activation.

The `verified_by_trusted_cli` field is a boundary **assertion**, not a cryptographic proof. Until the adopter implements and independently validates it, it MUST be treated as untrusted and no result may be automatically applied; disabling `auto_apply_enabled` returns to the previous owner-only workflow. Any policy/config change changes the digest and invalidates prior approval. No feedback entry is fabricated for this draft.

Only `review`/`remediation_review` may be enabled for automatic application in v1 (`AUTO_PHASES`, equal to the policy `enabled_phases`); the other proposal phases can only be suggested (see "Version 1.1: proposal phases"). `planning` and older data are excluded; no inferred conversion. The independent reviewer, triager and main thread cannot grant themselves scope override, merge, write to feedback_ledger, or authorization. Any contradiction with the owner's prior decision is a stop and escalation, not silent reclassification.

## Follow-on integration contract

- #783: create separate verified triage artifact bound to source context; do not accept user-controlled `reviewer_verified` assertions as evidence.
- #784: suggest-only ingestion, keep reviewer artifact and triage artifact separate, no disposition or verdict change.
- #785: enable only owner-approved `fix-here`/`advisory` paths after ledger, STOP and Karte validation; require committed advisory evidence.
- #786: conditionally enable `deferred` only with #683 recipient verification and handoff; measure errors and implement rollback.
- Automated reviewer/triager decisions alone never authorize an action. The user remains the final merge authority.
