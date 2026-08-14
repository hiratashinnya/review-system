# time_fixture_lint — time-dependent test data checker

Detects test data (absolute dates / fixed epochs) that is compared against a **live wall
clock** without that clock being controlled, before a code-free time-passage regression
bites `main` for a third time (issue #344).

## Why this exists

- **1st occurrence = #302** (2026-08-04): `tests/unit/test_codex_rate_limit_api.py` had a
  fixed epoch (`RL_RESET_EPOCH = 1783767886`) compared against a live-clock-derived
  window; it went stale and broke `main` with no code change.
- **2nd occurrence = #339**: the fix for #302 only covered that one file. Meanwhile
  `tests/fixtures/blocker_gate/waiver_valid.yml`'s `expires_at: "2026-08-08T00:00:00Z"`
  is compared against `datetime.now(timezone.utc)` in `blocker_gate/waiver.py:301`
  (`approved <= now < expires`, called from `blocker_gate/resolver.py:233`). It stayed
  green only because the *current* consuming tests happen to freeze/inject `now`
  — but nothing enforced that a *new* test using the same fixture would do the same,
  and the fixture's own date silently drifted into the past (today is 2026-08-10, four
  days past that `expires_at`).

There was no discipline written down, and no machine check — just two coincidences that
happened to keep tests protected. This tool makes the requirement checkable.

## Scoping (avoiding the naive-grep trap)

A blind `grep` for absolute dates across `tests/` hits ~17 fixtures / 9 tests, and most of
them are harmless — e.g. the 14 `blocker_gate` snapshot fixtures' `fetched_at` field is
only ever used in a **lower-bound** comparison
(`blocker_gate/contract.py`: `_date(result["fetched_at"]) > _date(result["completed_at"])`)
where `completed_at` is always derived from the real, ever-advancing clock — a fixed past
`fetched_at` can never become `>` a value that keeps moving forward, so it can never
regress no matter how much time passes.

So this tool does **not** flag every absolute date. It narrows to field/constant names
that plausibly represent **a validity-window boundary compared against wall clock** —
`expires_at` / `approved_at` / `resets_at` (and camelCase `resetsAt`) / `expiry` /
`deadline` / `valid_until` / `not_after` / `not_before` — and ignores decorative or
non-wall-clock fields like `created_at` / `fetched_at` / `completed_at` / `id`.

**Both ends of the window are in scope, not just the upper/expiry side** (PR #349
remediation, F-344-02): `approved_at`/`not_before` (window start) are just as unsafe as
`expires_at`/`valid_until`/`deadline`/`not_after`/`resets_at` (window end). The
determining factor isn't which side of the window a field names — it's whether the
literal, as authored, could sit on the "not yet flipped" side of `now` such that time
passing flips the comparison. `blocker_gate/waiver.py:301`'s `approved <= now < expires`
compares *both* fields to the same wall clock: an `expires_at` authored just past "now"
goes stale exactly like #339 did; symmetrically, an `approved_at` authored in the future
(to represent "not yet approved") would flip from `False` to `True` as real time catches
up to it — the same class of silent, code-free breakage, just mirrored. What's actually
**out of scope** is a comparison that never touches wall clock at all: `fetched_at` vs
`completed_at` in `blocker_gate/contract.py` compares two fixed fields from the same
snapshot, neither of which is `datetime.now()`/`time.time()`.

Two detectors, both scoped to **the reference site**, not the whole file (PR #349
remediation, F-344-01 — see "Protection scope" below):

1. **Fixture detector** — scans `tests/fixtures/**/*.{yml,yaml,json}` for those field
   names with an absolute-date/epoch value (double-quoted, single-quoted, or bare YAML
   values, and one-line inline JSON — F-344-03), finds the `tests/unit/*.py` files that
   reference the fixture (by filename), and requires **each occurrence's protection
   scope** to contain a clock-control marker (`unittest.mock.patch(...)` on a
   clock-related target, `now=datetime(...)` injection, `freeze_time(...)`/`freezegun`).
   No referencing test at all → reported as `no_consumer` (can't verify protection,
   surfaced rather than silently passed).
2. **Python-literal detector** — scans `tests/unit/*.py` for the same field names in
   inline dict literals (single line, single or multiple fields), and for bare
   fixed-epoch constant assignments (`NAME = 1783760000`-shaped). A hit is safe if
   **its own protection scope** has a clock-control marker, or the literal sits inside a
   `time.time()`-relative expression (the pattern #302 was fixed with — e.g.
   `int(time.time()) + 3600`).

### Protection scope (PR #349 remediation, F-344-01)

The original implementation searched the **entire referencing file's text** for a
protection marker — so a clock-*unrelated* `patch(...)` anywhere in a 300-line test file
(e.g. `patch("blocker_gate.cli.resolve_github_token")`) made the whole file "protected",
meaning a *new*, genuinely unprotected test added to that same file would still pass.
That's the exact false-negative #339 slipped through, just not yet exploited.

The scanner now parses each referencing file with `ast` and, for each occurrence line,
builds a scope from:

- the function/method directly enclosing the reference,
- if that's a method, the enclosing class's `setUp`/`setUpClass` (unittest calls these
  implicitly, so they count even without an explicit call at the reference site), and
- any other function in the same file connected to it by a **local call edge**
  (`foo()`/`self.foo()` resolved by simple name), transitively, undirected — this
  models the common pattern where one helper builds fixture data and a *different*
  helper (called by the same test method) does the clock patching (see
  `test_blocker_gate_contract_cli.py`'s `waiver_material()` + `evaluate_during_waiver_validity()`).

A `patch(...)` call only counts as protection if its target string looks clock-related
(`datetime`/`time`/`clock`/`freeze`, word-bounded so `resolve_github_token` doesn't
match) — a same-function, clock-unrelated `patch(...)` no longer masks an unprotected
reference either.

**Known residual limitations** (documented rather than silently accepted, same posture
as Issue #129's static-gate limits):

- A module-level reference (outside any function) can't be scoped down further and
  falls back to whole-file search, same as before.
- The local-call graph is **undirected and per-file**, not a true call-graph with
  caller/callee distinction. If a shared helper function is called by both a
  clock-protected test *and* a new, unprotected test, the new test's occurrence can
  still be masked as "protected" because it's in the same connected component as the
  protected caller. Precisely separating callers of a shared helper would require
  call-site-specific data-flow analysis beyond what this static, regex/AST tool does.
  When a fixture is used by tests that need clock protection *and* tests that
  structurally never reach a wall-clock comparison (e.g. schema-parsing-only tests),
  the fix used in this repo is to **split the fixture** (see
  `tests/fixtures/blocker_gate/schema_only_waiver.yml`) rather than rely on this edge
  case.

## Handling false positives: explicit, justified allowlist

Some hits are genuinely inert but don't fit either safety pattern above — e.g.
`test_codex_rate_limit_api.py`'s `REAL_IDLE_RESULT["...']["resetsAt"]` is a **live-captured
API response** fed straight into a pure function
(`summarize_rate_limits(response, now)`) that takes `now` as an explicit parameter and
never reads a real clock; likewise its paired `NOW = 1783760000` constant. Neither will
ever touch `datetime.now()`/`time.time()`, so there's nothing to mock.

These are recorded — not silently ignored — in `time_fixture_lint/allowlist.py` as
`(path, name, reason)` entries, matching this repo's existing convention in
`asset_parity/exceptions.py` ("don't invent the exception at runtime; record the decision,
then reference it"). Adding a new allowlist entry requires citing *why* the value never
reaches a live clock read (a specific function signature / call site), not just "looks
fine".

## Usage

```bash
python3 -m time_fixture_lint check
python3 -m time_fixture_lint check --root /path/to/repo
```

Exit codes: `0` no violations (protected + allowlisted + no findings all pass) /
`1` at least one `violation` or `no_consumer` hit / `2` usage error (argparse default).

## Existing repo survey (Issue #344, at authoring time; updated PR #349 remediation)

Running the tool against this repo today finds 0 violations:

- `tests/fixtures/blocker_gate/waiver_valid.yml`, `waiver_expired.yml`
  (`approved_at`/`expires_at`, 2 each) — **protected**. `waiver_valid.yml` is referenced
  from `test_blocker_gate_contract_cli.py` (via `waiver_material()`, whose caller test
  methods also call `evaluate_during_waiver_validity()` — the two are connected through
  each calling test method, and the latter patches `blocker_gate.resolver.datetime`) and
  from `test_blocker_gate_waiver.py::WaiverVerifierTests.setUp` (which injects `now=`
  directly). `waiver_expired.yml` is referenced only from the same protected `setUp`.
- `tests/fixtures/blocker_gate/schema_only_waiver.yml`,
  `tests/fixtures/blocker_gate/waiver_unknown_key.yml` (`approved_at`/`expires_at`, 2
  each) — **allowlisted**. Both are consumed only by
  `test_blocker_gate_waiver.py::WaiverParserTests`, which calls `parse_waiver_yaml()`/
  `parse_policy_yaml()` for schema-validation tests only — that code path never calls
  `verify_waiver()` (the function that does the wall-clock comparison), so the dates are
  opaque strings here. `schema_only_waiver.yml` was split out of `waiver_valid.yml`
  (PR #349, F-344-01 remediation) specifically because `waiver_valid.yml` is *also*
  consumed by clock-comparing tests elsewhere — see "Known residual limitations" above
  for why the split, rather than a smarter scope, was the fix.
- `tests/unit/test_blocker_gate_contract_cli.py:238` (`expires_at` inline JSON literal
  used to build a fake waiver payload) — **protected**: the enclosing test method
  (`test_waiver_evidence_correlation_is_closed`) calls `evaluate_during_waiver_validity()`
  directly, which patches `blocker_gate.resolver.datetime`.
- `tests/unit/test_codex_rate_limit_api.py` (`resetsAt`, `NOW`) — **allowlisted** (see
  above).

The other fixtures/files the issue's naive-grep count included (the 14
`fetched_at`-only JSON snapshots, `test_blocker_gate_github.py`'s API-version-header
string, ID-embedded dates in `test_domain.py`/`test_workspace_git.py`, decision-date code
comments) never match the suspicious-field vocabulary at all, so they don't appear in the
tool's output — that's the point of the scoping above, not an oversight.

## Module map

| Module | Responsibility |
|---|---|
| `scanner.py` | Field vocabulary, fixture/python-literal detectors, `Finding`/`Report` |
| `allowlist.py` | Documented intentional inert hits |
| `cli.py` | `python3 -m time_fixture_lint check` |

## CI wiring

`.github/workflows/tests.yml` runs `python3 -m time_fixture_lint check` as a step
alongside the full unit test suite on every `pull_request` (see that workflow's own
comments for the `pages.yml` role-separation rationale). A `violation`/`no_consumer` hit
fails the build; a `protected`/`allowlisted` hit is informational only.
