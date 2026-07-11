"""Unit tests for the Codex rate-limit banner detection regex (Issue #182).

NOTE (Issue #195): as of the structured-API work, this pane-text regex is no
longer the *primary* rate-limit detector — the hooks now call Codex's
``account/rateLimits/read`` app-server method first (see
``test_codex_rate_limit_api.py``). The regex below is retained only as the
*fallback* path used when that API is unavailable (codex not on PATH, not
logged in, app-server error/timeout, or an older Codex without the method), so
these tests still guard that fallback and remain valid.

`RATE_LIMIT_RE` in `.codex/hooks/codex-rate-limit-stop-hook.sh` and
`.codex/hooks/codex-rate-limit-watcher.sh` used to be a single broad `OR` of
loose terms (bare "rate limit", "usage limit", "too many requests", ...).
Those words are common in ordinary coding conversation, so the gate could
false-fire and end with an unattended `continue` being injected into a tmux
pane. Both scripts now require two independent regexes
(`RATE_LIMIT_PHRASE_RE` AND `RATE_LIMIT_RESET_RE`) to both match before
treating text as a real rate-limit banner, plus a 2-consecutive-poll debounce
before the "no parseable reset time" fallback path is armed.

Both hook scripts can be `source`d with `CODEX_RL_SOURCE_FOR_TEST=1` (and, for
the watcher, a dummy pane-id positional arg) to expose their pure
text-matching functions for direct testing without touching tmux.
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STOP_HOOK = ROOT / ".codex" / "hooks" / "codex-rate-limit-stop-hook.sh"
WATCHER = ROOT / ".codex" / "hooks" / "codex-rate-limit-watcher.sh"

# Real banner text captured in a Stop payload (PR #66):
#   "You've hit your session limit · resets 10:50pm (Asia/Tokyo)"
REAL_BANNER_EXAMPLE = "You've hit your session limit · resets 10:50pm (Asia/Tokyo)"

TRUE_POSITIVES = [
    ("real captured banner (PR #66)", REAL_BANNER_EXAMPLE),
    ("weekly limit banner", "You've hit your weekly limit · resets Mon"),
    (
        "usage limit + relative try-again",
        "You've hit your usage limit. Try again in 3h29m, "
        "or upgrade your plan for more access.",
    ),
    ("429 + too many requests + retry", "429 Too Many Requests. retry after 30s."),
    ("limit reached + resets HH:MM", "usage limit reached. resets 9:00am"),
]

# Ordinary dev-conversation text that must NOT arm the recovery flow, because
# it merely mentions rate/usage/session/request "limit" or "too many
# requests" without the real banner's phrase+reset-cue pairing.
FALSE_POSITIVES = [
    (
        "discussing implementing rate limiting",
        "Let's add rate limiting to this API endpoint so we don't get "
        "too many requests.",
    ),
    (
        "pasted unrelated 429 log mentioning session limit",
        "I hit an error: too many requests to the upstream service, "
        "need to add a session limit.",
    ),
    (
        "spec text about a request limit",
        "We should implement a request limit of 100rpm and log a "
        "warning at 80% usage.",
    ),
    (
        "unrelated HTTP 429 without 'too many requests' wording",
        "Someone reported HTTP 429 errors intermittently; check the "
        "rate limiter config.",
    ),
    (
        "unrelated 'resets' without limit-hit phrase",
        "resets at 9am daily for the cron job cache.",
    ),
    (
        "unrelated 'try again' without limit-hit phrase",
        "Try again in 5 minutes if the build fails.",
    ),
]

# A banner that matches the AND regex but that parse_reset_from_text cannot
# extract a concrete reset time from (used to exercise the acquire loop's
# no-reset-time / debounce path without falling straight through on attempt 1).
DEBOUNCE_FIXTURE = (
    "You've hit your usage limit. Try again after attempt 2 today."
)


def _run(script_body, args=()):
    return subprocess.run(
        ["bash", "-c", script_body, "bash", *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def stop_hook_has_rate_limit_text(payload, pane_tail):
    body = f'''
set -u
export CODEX_RL_SOURCE_FOR_TEST=1
source "{STOP_HOOK}"
has_rate_limit_text "$1" "$2"
'''
    result = _run(body, [payload, pane_tail])
    return result.returncode == 0


def watcher_text_has_rate_limit_banner(text):
    body = f'''
set -u
export CODEX_RL_SOURCE_FOR_TEST=1
source "{WATCHER}" dummy-pane
text_has_rate_limit_banner "$1"
'''
    result = _run(body, [text])
    return result.returncode == 0


def watcher_parse_reset_from_text(text):
    body = f'''
set -u
export CODEX_RL_SOURCE_FOR_TEST=1
source "{WATCHER}" dummy-pane
parse_reset_from_text "$1"
'''
    result = _run(body, [text])
    return result.stdout


def _extract_default_regex(script_path, var_name):
    """Extract the `${VAR:-default}` value as bash actually resolves it,
    by sourcing the script in test mode with the override env var unset and
    printing the resulting variable."""
    body = f'''
set -u
export CODEX_RL_SOURCE_FOR_TEST=1
source "{script_path}" dummy-pane 2>/dev/null || source "{script_path}"
printf '%s' "${var_name}"
'''
    result = subprocess.run(
        ["bash", "-c", body],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout


class RateLimitBannerRegexTests(unittest.TestCase):
    def test_scripts_pass_bash_syntax_check(self):
        for script in (STOP_HOOK, WATCHER):
            with self.subTest(script=script.name):
                result = subprocess.run(
                    ["bash", "-n", str(script)],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(
                    result.returncode, 0, f"bash -n failed: {result.stderr}"
                )

    def test_stop_hook_true_positives(self):
        for desc, text in TRUE_POSITIVES:
            with self.subTest(desc=desc):
                self.assertTrue(
                    stop_hook_has_rate_limit_text("", text),
                    f"expected has_rate_limit_text to match: {text!r}",
                )

    def test_stop_hook_false_positives(self):
        for desc, text in FALSE_POSITIVES:
            with self.subTest(desc=desc):
                self.assertFalse(
                    stop_hook_has_rate_limit_text("", text),
                    f"expected has_rate_limit_text NOT to match: {text!r}",
                )

    def test_watcher_true_positives(self):
        for desc, text in TRUE_POSITIVES:
            with self.subTest(desc=desc):
                self.assertTrue(
                    watcher_text_has_rate_limit_banner(text),
                    f"expected text_has_rate_limit_banner to match: {text!r}",
                )

    def test_watcher_false_positives(self):
        for desc, text in FALSE_POSITIVES:
            with self.subTest(desc=desc):
                self.assertFalse(
                    watcher_text_has_rate_limit_banner(text),
                    f"expected text_has_rate_limit_banner NOT to match: {text!r}",
                )

    def test_stop_hook_and_watcher_regex_are_consistent(self):
        # Both scripts must agree on what counts as a real banner, otherwise
        # the Stop hook's gate and the watcher's own scanning can disagree.
        for var in ("RATE_LIMIT_PHRASE_RE", "RATE_LIMIT_RESET_RE"):
            with self.subTest(var=var):
                stop_val = _extract_default_regex(STOP_HOOK, var)
                watcher_val = _extract_default_regex(WATCHER, var)
                self.assertEqual(stop_val, watcher_val)
                self.assertTrue(stop_val, f"{var} default must not be empty")

    def test_regression_parse_reset_from_text_still_extracts_real_examples(self):
        # Regression check for AC#3: legitimate recovery (PR #86's verified
        # extraction cases) must still work after tightening the gate regex.
        epoch = watcher_parse_reset_from_text("session limit ... resets 8:50am").strip()
        self.assertRegex(epoch, r"^\d+$")

        weekly = watcher_parse_reset_from_text("resets Mon 9am").strip()
        self.assertEqual(weekly, "WEEKLY")

        epoch2 = watcher_parse_reset_from_text("resets 11:05pm").strip()
        self.assertRegex(epoch2, r"^\d+$")

    def test_regression_real_banner_example_round_trips(self):
        # The exact real captured Stop payload text (PR #66) must both pass
        # the (tightened) banner gate and still yield a parseable reset time.
        self.assertTrue(watcher_text_has_rate_limit_banner(REAL_BANNER_EXAMPLE))
        epoch = watcher_parse_reset_from_text(REAL_BANNER_EXAMPLE).strip()
        self.assertRegex(epoch, r"^\d+$")

    def test_debounce_fixture_matches_banner_but_has_no_parseable_reset(self):
        # Sanity-check the fixture used by the acquire-loop debounce test
        # below: it must satisfy the AND banner regex but NOT let
        # parse_reset_from_text extract a concrete time, so the acquire loop
        # actually exercises its streak-counting path instead of exiting on
        # attempt 1 via a parsed reset_epoch.
        self.assertTrue(watcher_text_has_rate_limit_banner(DEBOUNCE_FIXTURE))
        self.assertEqual(watcher_parse_reset_from_text(DEBOUNCE_FIXTURE), "")

    def test_acquire_loop_requires_two_consecutive_banner_confirmations(self):
        # Extra-confirmation-step regression test (AC#2): a single-snapshot
        # banner sighting must not be enough to consider the banner
        # "confirmed" (saw_banner=1); it must reappear on a second
        # consecutive poll first. Verified via the watcher's own log output,
        # with tmux/pane access stubbed out and all polling delays zeroed so
        # the loop runs instantly and deterministically.
        state_dir = tempfile.mkdtemp(prefix="codex-rl-test-")
        try:
            body = f'''
set -u
export CODEX_RL_SOURCE_FOR_TEST=1
export CODEX_RL_STATE_DIR="{state_dir}"
export CODEX_RL_RESET_POLL_INTERVAL=0
export CODEX_RL_RESET_POLL_MAX=3
export CODEX_RL_BANNER_POLL_INTERVAL=0
export CODEX_RL_BANNER_POLL_MAX=1
source "{WATCHER}" dummy-pane

FIXTURE_TEXT="$1"
is_codex_pane() {{ return 0; }}
is_working() {{ return 1; }}
pane_text() {{ printf '%s' "$FIXTURE_TEXT"; }}

wait_for_reset_and_recover
'''
            result = _run(body, [DEBOUNCE_FIXTURE])
            self.assertEqual(result.returncode, 0, result.stderr)

            log_path = Path(state_dir) / "watcher.log"
            self.assertTrue(log_path.exists(), "watcher.log was not written")
            log_text = log_path.read_text()

            self.assertIn("banner_seen=0; banner_streak=1", log_text)
            self.assertIn("banner_seen=1; banner_streak=2", log_text)
            # Never actually injects on this no-reset-time, always-present
            # fixture (banner never "clears", so the fallback correctly
            # refuses to guess-fire).
            self.assertNotIn("send '", log_text)
            self.assertIn("no blind injection", log_text)
        finally:
            shutil.rmtree(state_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
