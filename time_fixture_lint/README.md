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
that plausibly mean "the upper bound of a validity window" —
`expires_at` / `approved_at` / `resets_at` (and camelCase `resetsAt`) / `expiry` /
`deadline` / `valid_until` / `not_after` / `not_before` — and ignores decorative or
lower-bound fields like `created_at` / `fetched_at` / `completed_at` / `id`.

Two detectors:

1. **Fixture detector** — scans `tests/fixtures/**/*.{yml,yaml,json}` for those field
   names with an absolute-date/epoch value, finds the `tests/unit/*.py` files that
   reference the fixture (by filename), and requires each of them to contain a
   clock-control marker (`unittest.mock.patch(...)`, `now=datetime(...)` injection,
   `freeze_time(...)`/`freezegun`). No referencing test at all → reported as
   `no_consumer` (can't verify protection, surfaced rather than silently passed).
2. **Python-literal detector** — scans `tests/unit/*.py` for the same field names in
   inline dict literals, and for bare fixed-epoch constant assignments
   (`NAME = 1783760000`-shaped). A hit is safe if the same file has a clock-control
   marker, or the literal sits inside a `time.time()`-relative expression (the pattern
   #302 was fixed with — e.g. `int(time.time()) + 3600`).

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

## Existing repo survey (Issue #344, at authoring time)

Running the tool against this repo today finds 9 suspicious-field hits, 0 violations:

- `tests/fixtures/blocker_gate/waiver_valid.yml`, `waiver_expired.yml`,
  `waiver_unknown_key.yml` (`approved_at`/`expires_at`, 2 each) — **protected**, all
  referencing tests (`test_blocker_gate_contract_cli.py`, `test_blocker_gate_waiver.py`)
  patch or inject the clock.
- `tests/unit/test_blocker_gate_contract_cli.py:238` (`expires_at` inline JSON literal
  used to build a fake waiver payload) — **protected** by the same file's
  `patch("blocker_gate.resolver.datetime", ...)`.
- `tests/unit/test_codex_rate_limit_api.py` (`resetsAt`, `NOW`) — **allowlisted** (see
  above).

The other ~8 fixtures / files the issue's naive-grep count included (the 14
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
