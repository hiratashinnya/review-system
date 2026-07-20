"""Unit tests for the Claude Code rate-limit auto-resume bash hooks (Issue #240).

Covers the pure, side-effect-light logic in
``.claude/hooks/resume-watcher.sh`` (and the shared ``lib-pane-guard.sh``),
which previously had NO automated coverage — only the Codex-side hooks did
(``test_codex_rate_limit_*``). Issue #240 D2 flagged this coverage gap.

``resume-watcher.sh`` can be sourced with ``CLAUDE_RL_SOURCE_FOR_TEST=1`` (and a
dummy pane-id positional arg) to expose its pure functions
(``parse_reset_from_text`` / ``build_continue_msg`` / ``text_has_banner`` / the
lib's ``rl_pane_slug`` / ``rl_hit_file``) without touching tmux, acquiring the
lock, or running the wait/inject loops — the same test hook the Codex watcher
uses (``CODEX_RL_SOURCE_FOR_TEST``). ``CLAUDE_RL_STATE_DIR`` redirects state
(logs / lock) into a temp dir so tests never write to ``~/.claude``.

The tests double as regression guards for the bug fixes made in this issue:
  * B1 — banner scan window unified (``BANNER_SCAN_LINES``, default 40).
  * B2 — reset regex accepts ``resets at 3pm`` / ``resets at Mon`` ("at" form).
  * B3 — a just-passed reset time is NOT rolled ~24h into tomorrow.
"""

import datetime
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK_DIR = ROOT / ".claude" / "hooks"
LIB = HOOK_DIR / "lib-pane-guard.sh"
HOOK = HOOK_DIR / "on-rate-limit.sh"
WATCHER = HOOK_DIR / "resume-watcher.sh"
_HAS_BASH = shutil.which("bash") is not None


def _run(script_body, args=(), env_lines=""):
    """Source the watcher in test mode inside a temp state dir, then run
    ``script_body`` with positional ``args`` available as $1, $2, ..."""
    state_dir = tempfile.mkdtemp(prefix="claude-rl-test-")
    try:
        body = f'''
set -u
export CLAUDE_RL_SOURCE_FOR_TEST=1
export CLAUDE_RL_STATE_DIR="{state_dir}"
{env_lines}
source "{WATCHER}" dummy-pane
{script_body}
'''
        return subprocess.run(
            ["bash", "-c", body, "bash", *args],
            capture_output=True,
            text=True,
            timeout=30,
        )
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def parse_reset(text):
    return _run('parse_reset_from_text "$1"', [text]).stdout


def text_has_banner(text):
    return _run('text_has_banner "$1"', [text]).returncode == 0


def build_msg(hit_str="", reset_epoch="", override=""):
    body = (
        'HIT_STR="$1"; reset_epoch="$2"; CONTINUE_MSG_OVERRIDE="$3"; '
        "build_continue_msg"
    )
    return _run(body, [hit_str, reset_epoch, override]).stdout


def extract_var(var_name):
    """Resolve a ``${VAR:-default}`` config value as bash actually sets it."""
    return _run(f'printf "%s" "${var_name}"').stdout


@unittest.skipUnless(_HAS_BASH, "bash バイナリが必要")
class RateLimitHookTests(unittest.TestCase):
    def test_scripts_pass_bash_syntax_check(self):
        for script in (LIB, HOOK, WATCHER):
            with self.subTest(script=script.name):
                result = subprocess.run(
                    ["bash", "-n", str(script)], capture_output=True, text=True
                )
                self.assertEqual(
                    result.returncode, 0, f"bash -n failed: {result.stderr}"
                )

    # --- B2: reset regex must accept the "at" form ---------------------------
    def test_b2_reset_with_at_is_parsed(self):
        for text in (
            "You've hit your usage limit · limit resets at 3pm (Asia/Tokyo)",
            "limit resets at 11:59pm",
            "usage limit reached. resets at 9:00am",
        ):
            with self.subTest(text=text):
                self.assertRegex(
                    parse_reset(text).strip(),
                    r"^\d+$",
                    f"expected an epoch for {text!r}",
                )

    def test_reset_without_at_still_parsed(self):
        # Regression: the pre-existing "digit right after resets" form must
        # keep working after adding the optional "at".
        for text in ("resets 3pm", "session limit ... resets 10:50pm"):
            with self.subTest(text=text):
                self.assertRegex(parse_reset(text).strip(), r"^\d+$")

    def test_weekly_limit_detected_with_and_without_at(self):
        self.assertEqual(parse_reset("hit your weekly limit resets Mon").strip(), "WEEKLY")
        self.assertEqual(parse_reset("resets at Mon 9am").strip(), "WEEKLY")

    def test_no_reset_time_returns_empty(self):
        self.assertEqual(parse_reset("nothing to see here").strip(), "")

    # --- B3: a just-passed reset must not roll ~24h into tomorrow ------------
    def test_b3_just_passed_reset_not_rolled_to_tomorrow(self):
        now = datetime.datetime.now()
        # Avoid the midnight-crossing ambiguity: "a few minutes ago" must stay
        # on the same calendar day for this assertion to be meaningful.
        if now.hour == 0 and now.minute < 30:
            self.skipTest("near midnight; same-day 'past' assumption unsafe")
        past = now - datetime.timedelta(minutes=2)
        hhmm = past.strftime("%I:%M%p").lstrip("0").lower()  # e.g. "3:07pm"
        epoch = parse_reset(f"limit resets {hhmm}").strip()
        self.assertRegex(epoch, r"^\d+$")
        now_epoch = int(now.timestamp())
        # Within grace → treated as "just now", a few minutes in the past;
        # the pre-fix bug rolled this to tomorrow (~86400s away).
        self.assertLess(
            abs(int(epoch) - now_epoch),
            4000,
            "just-passed reset was wrongly rolled ~24h into tomorrow (B3)",
        )

    def test_future_reset_today_is_used_as_is(self):
        now = datetime.datetime.now()
        if now.hour >= 21:
            self.skipTest("near end of day; +2h may cross midnight")
        future = now + datetime.timedelta(hours=2)
        hhmm = future.strftime("%I:%M%p").lstrip("0").lower()
        epoch = parse_reset(f"limit resets {hhmm}").strip()
        self.assertRegex(epoch, r"^\d+$")
        delta = int(epoch) - int(now.timestamp())
        self.assertTrue(0 < delta < 3 * 3600, f"unexpected delta {delta}")

    # --- text_has_banner regex (B2 also widens the banner detector) ----------
    def test_banner_detector_matches_at_form(self):
        self.assertTrue(text_has_banner("limit resets at 3pm"))
        self.assertTrue(text_has_banner("You've hit your session limit"))
        self.assertTrue(text_has_banner("resets Mon"))

    def test_banner_detector_ignores_unrelated_text(self):
        self.assertFalse(text_has_banner("just a normal line of output"))

    # --- build_continue_msg --------------------------------------------------
    def test_build_msg_includes_available_time_parts(self):
        now_epoch = str(int(datetime.datetime.now().timestamp()))
        msg = build_msg(hit_str="2026-07-20 10:00:00", reset_epoch=now_epoch)
        self.assertIn("解除されました", msg)
        self.assertIn("検知 2026-07-20 10:00:00", msg)
        self.assertIn("解除", msg)
        self.assertIn("現在", msg)

    def test_build_msg_omits_missing_parts(self):
        # No HIT_STR and no reset_epoch → only the "現在" clause, no 検知/解除.
        msg = build_msg(hit_str="", reset_epoch="")
        self.assertIn("現在", msg)
        self.assertNotIn("検知", msg)

    def test_build_msg_respects_override(self):
        msg = build_msg(override="CUSTOM RESUME TEXT")
        self.assertEqual(msg, "CUSTOM RESUME TEXT")

    # --- shared lib helpers --------------------------------------------------
    def test_pane_slug_normalizes_non_alnum(self):
        self.assertEqual(_run('rl_pane_slug "%3"').stdout, "_3")
        self.assertEqual(_run('rl_pane_slug "pane-1.2"').stdout, "pane_1_2")

    def test_hit_file_path_uses_state_dir_and_slug(self):
        out = _run('rl_hit_file "%7"').stdout
        self.assertTrue(out.endswith("/hit-time._7"), out)

    def test_default_pane_cmd_re_includes_bun_and_deno(self):
        # B5: default foreground pattern widened beyond node.
        re_default = extract_var("RL_PANE_CMD_RE")
        for runtime in ("claude", "node", "bun", "deno"):
            self.assertIn(runtime, re_default)

    # --- B1: banner scan window is a single shared constant, default 40 ------
    def test_banner_scan_lines_default_is_40(self):
        self.assertEqual(extract_var("BANNER_SCAN_LINES").strip(), "40")

    def test_acquire_capture_and_limit_screen_share_scan_window(self):
        # Both the acquire-loop capture and is_limit_screen must read the same
        # BANNER_SCAN_LINES window, or a banner on lines 16-40 is "detected but
        # invisible to the clear check" (B1). Guard structurally via source.
        src = WATCHER.read_text()
        self.assertIn('tail -n "$BANNER_SCAN_LINES"', src)
        self.assertIn('pane_tail "$BANNER_SCAN_LINES"', src)


if __name__ == "__main__":
    unittest.main()
