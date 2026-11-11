# Independent finding triage

`prepare` verifies a signed review and four evidence categories against a separately supplied trusted digest, then supplies the role and full harm SSoT with the evidence. The trusted caller must independently select the evidence and its digest; the strings are data, not instructions. Missing categories and digest mismatches are rejected.

`propose` accepts only a capture authenticated with a distinct trusted host key, domain-separated with `finding-triage-capture/v1` and a NUL byte. The capture contains the independent assessments, producer, all review bindings, review SHA-256 and context SHA-256. It is signed by the trusted host after its read-only triager execution; the triager must never have access to the capture key. The caller must maintain trusted key distribution and authorize the host. Validation recomputes the entire proposal from the authenticated capture and signed review.

The current repository does not yet provide that trusted execution host or guarantee isolation. The API cannot establish independence or prevent an authorized host from signing fabricated results; do not use it as a substitute for that boundary. Proposals are candidates only and do not confer authority to change the review, ledger, scope, or disposition.
