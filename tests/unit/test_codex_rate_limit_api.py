"""Unit tests for the structured Codex rate-limit API detection (Issue #195).

Issue #195 replaces tmux pane text scraping as the *primary* rate-limit signal
with a call to Codex's structured ``account/rateLimits/read`` app-server method
(via ``.codex/hooks/codex-rate-limit-query.py``). The old regex path
(``test_codex_rate_limit_banner_regex.py``) is retained only as a fallback for
when the API is unavailable, so those tests still hold; these tests cover the
new API path:

- the pure response-classification helpers in ``codex-rate-limit-query.py``
  (``summarize_rate_limits`` / ``pick_binding_window``) against captured and
  synthetic ``account/rateLimits/read`` results;
- the helper's process-driving / failure fallback behavior end-to-end via a
  fake app-server;
- the bash ``query_rate_limit_api`` parser and ``wait_until_epoch_and_recover``
  flow in ``codex-rate-limit-watcher.sh`` / ``codex-rate-limit-stop-hook.sh``,
  with the API command and tmux/pane access stubbed out.
"""

import importlib.util
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STOP_HOOK = ROOT / ".codex" / "hooks" / "codex-rate-limit-stop-hook.sh"
WATCHER = ROOT / ".codex" / "hooks" / "codex-rate-limit-watcher.sh"
QUERY_HELPER = ROOT / ".codex" / "hooks" / "codex-rate-limit-query.py"


def _load_query_module():
    spec = importlib.util.spec_from_file_location(
        "codex_rate_limit_query", str(QUERY_HELPER)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


QMOD = _load_query_module()

# Real result captured live from `codex app-server --stdio`
# account/rateLimits/read on codex-cli 0.144.1 (Issue #195 verification):
# not currently limited (rateLimitReachedType == null).
REAL_IDLE_RESULT = {
    "rateLimits": {
        "limitId": "codex",
        "limitName": None,
        "primary": {
            "usedPercent": 1,
            "windowDurationMins": 300,
            "resetsAt": 1783767886,
        },
        "secondary": {
            "usedPercent": 0,
            "windowDurationMins": 10080,
            "resetsAt": 1784354686,
        },
        "credits": {"hasCredits": False, "unlimited": False, "balance": "0"},
        "individualLimit": None,
        "planType": "plus",
        "rateLimitReachedType": None,
    }
}

NOW = 1783760000  # a fixed "now" a bit before the captured reset times


class SummarizeRateLimitsTests(unittest.TestCase):
    def test_idle_snapshot_is_not_reached(self):
        fields = QMOD.summarize_rate_limits(REAL_IDLE_RESULT, NOW)
        self.assertEqual(fields["RL_OK"], 1)
        self.assertEqual(fields["RL_REACHED"], 0)
        self.assertEqual(fields["RL_REACHED_TYPE"], "")
        self.assertEqual(fields["RL_PLAN"], "plus")
        # Even when idle, the highest-usage future window is surfaced.
        self.assertEqual(fields["RL_RESET_EPOCH"], 1783767886)
        self.assertEqual(fields["RL_WINDOW_MINS"], 300)
        self.assertEqual(fields["RL_USED_PERCENT"], 1)

    def test_reached_primary_window(self):
        result = {
            "rateLimits": {
                "primary": {
                    "usedPercent": 100,
                    "windowDurationMins": 300,
                    "resetsAt": 1783767886,
                },
                "secondary": {
                    "usedPercent": 40,
                    "windowDurationMins": 10080,
                    "resetsAt": 1784354686,
                },
                "planType": "plus",
                "rateLimitReachedType": "rate_limit_reached",
            }
        }
        fields = QMOD.summarize_rate_limits(result, NOW)
        self.assertEqual(fields["RL_REACHED"], 1)
        self.assertEqual(fields["RL_REACHED_TYPE"], "rate_limit_reached")
        # Binding window is the exhausted 5h window, not the 40% weekly one.
        self.assertEqual(fields["RL_RESET_EPOCH"], 1783767886)
        self.assertEqual(fields["RL_WINDOW_MINS"], 300)
        self.assertEqual(fields["RL_USED_PERCENT"], 100)

    def test_reached_weekly_window_is_the_binding_one(self):
        result = {
            "rateLimits": {
                "primary": {
                    "usedPercent": 20,
                    "windowDurationMins": 300,
                    "resetsAt": 1783767886,
                },
                "secondary": {
                    "usedPercent": 100,
                    "windowDurationMins": 10080,
                    "resetsAt": 1784354686,
                },
                "planType": "pro",
                "rateLimitReachedType": "workspace_owner_usage_limit_reached",
            }
        }
        fields = QMOD.summarize_rate_limits(result, NOW)
        self.assertEqual(fields["RL_REACHED"], 1)
        # The exhausted window is the weekly one; bash then treats its long
        # windowDurationMins as "do not auto-recover".
        self.assertEqual(fields["RL_RESET_EPOCH"], 1784354686)
        self.assertEqual(fields["RL_WINDOW_MINS"], 10080)

    def test_both_exhausted_waits_for_later_reset(self):
        result = {
            "rateLimits": {
                "primary": {
                    "usedPercent": 100,
                    "windowDurationMins": 300,
                    "resetsAt": 1783767886,
                },
                "secondary": {
                    "usedPercent": 100,
                    "windowDurationMins": 10080,
                    "resetsAt": 1784354686,
                },
                "rateLimitReachedType": "rate_limit_reached",
            }
        }
        fields = QMOD.summarize_rate_limits(result, NOW)
        # Must wait for the *latest* exhausted window to reset.
        self.assertEqual(fields["RL_RESET_EPOCH"], 1784354686)
        self.assertEqual(fields["RL_WINDOW_MINS"], 10080)

    def test_missing_snapshot_raises(self):
        with self.assertRaises(ValueError):
            QMOD.summarize_rate_limits({"unexpected": True}, NOW)


class QueryHelperProcessTests(unittest.TestCase):
    def _run_helper(self, env_extra):
        env = dict(os.environ)
        env.update(env_extra)
        return subprocess.run(
            ["python3", str(QUERY_HELPER)],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )

    def test_fake_app_server_round_trip(self):
        # A fake app-server that answers id=2 with a reached snapshot. It must
        # keep reading stdin (the helper deliberately keeps stdin open until it
        # has the reply), so this loops until EOF.
        fake = textwrap.dedent(
            """\
            #!/usr/bin/env bash
            while IFS= read -r line; do
              case "$line" in
                *'"id":2'*|*'"id": 2'*)
                  printf '%s\\n' '{"id":2,"result":{"rateLimits":{"primary":{"usedPercent":100,"windowDurationMins":300,"resetsAt":1783767886},"secondary":{"usedPercent":10,"windowDurationMins":10080,"resetsAt":1784354686},"planType":"plus","rateLimitReachedType":"rate_limit_reached"}}}'
                  ;;
              esac
            done
            """
        )
        tmp = tempfile.mkdtemp(prefix="codex-rl-fake-")
        try:
            fake_path = Path(tmp) / "fake-app-server.sh"
            fake_path.write_text(fake)
            fake_path.chmod(0o755)
            result = self._run_helper(
                {
                    "CODEX_RL_APP_SERVER_CMD": str(fake_path),
                    "CODEX_RL_API_TIMEOUT": "10",
                }
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("RL_OK=1", result.stdout)
            self.assertIn("RL_REACHED=1", result.stdout)
            self.assertIn("RL_REACHED_TYPE=rate_limit_reached", result.stdout)
            self.assertIn("RL_RESET_EPOCH=1783767886", result.stdout)
            self.assertIn("RL_WINDOW_MINS=300", result.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_missing_binary_reports_not_ok(self):
        result = self._run_helper(
            {"CODEX_RL_APP_SERVER_CMD": "/nonexistent/codex-xyz-not-here"}
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RL_OK=0", result.stdout)


def _run_bash(body, args=()):
    return subprocess.run(
        ["bash", "-c", body, "bash", *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


class BashQueryParsingTests(unittest.TestCase):
    """query_rate_limit_api must parse the helper's RL_* lines and signal
    success/fallback via its return code, in both hook scripts."""

    CANNED_REACHED = (
        "printf '%s\\n' RL_OK=1 RL_REACHED=1 "
        "RL_REACHED_TYPE=rate_limit_reached RL_RESET_EPOCH=1783767886 "
        "RL_WINDOW_MINS=300 RL_USED_PERCENT=100 RL_PLAN=plus"
    )

    def _source(self, script, positional=""):
        return f'''
set -u
export CODEX_RL_SOURCE_FOR_TEST=1
source "{script}" {positional}
'''

    def test_watcher_parses_reached(self):
        body = self._source(WATCHER, "dummy-pane") + f'''
export CODEX_RL_QUERY_CMD="{self.CANNED_REACHED}"
if query_rate_limit_api; then
  printf 'OK REACHED=%s TYPE=%s EPOCH=%s WIN=%s USED=%s PLAN=%s\\n' \
    "$RL_REACHED" "$RL_REACHED_TYPE" "$RL_RESET_EPOCH" "$RL_WINDOW_MINS" \
    "$RL_USED_PERCENT" "$RL_PLAN"
else
  printf 'FALLBACK\\n'
fi
'''
        result = _run_bash(body)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "OK REACHED=1 TYPE=rate_limit_reached EPOCH=1783767886 "
            "WIN=300 USED=100 PLAN=plus",
            result.stdout,
        )

    def test_stop_hook_parses_reached(self):
        body = self._source(STOP_HOOK) + f'''
export CODEX_RL_QUERY_CMD="{self.CANNED_REACHED}"
if query_rate_limit_api; then printf 'OK EPOCH=%s\\n' "$RL_RESET_EPOCH"; fi
'''
        result = _run_bash(body)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OK EPOCH=1783767886", result.stdout)

    def test_query_returns_fallback_when_not_ok(self):
        body = self._source(WATCHER, "dummy-pane") + '''
export CODEX_RL_QUERY_CMD="printf '%s\\n' RL_OK=0"
if query_rate_limit_api; then printf 'OK\\n'; else printf 'FALLBACK\\n'; fi
'''
        result = _run_bash(body)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("FALLBACK", result.stdout)
        self.assertNotIn("OK", result.stdout)

    def test_api_window_is_long_threshold(self):
        body = self._source(STOP_HOOK) + '''
export CODEX_RL_MAX_AUTO_WINDOW_MINS=360
RL_WINDOW_MINS=300; api_window_is_long && printf 'SHORT-LONG\\n' || printf 'SHORT-OK\\n'
RL_WINDOW_MINS=10080; api_window_is_long && printf 'WEEKLY-LONG\\n' || printf 'WEEKLY-OK\\n'
RL_WINDOW_MINS=""; api_window_is_long && printf 'EMPTY-LONG\\n' || printf 'EMPTY-OK\\n'
'''
        result = _run_bash(body)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SHORT-OK", result.stdout)
        self.assertIn("WEEKLY-LONG", result.stdout)
        self.assertIn("EMPTY-OK", result.stdout)


class BashEpochRecoveryTests(unittest.TestCase):
    """wait_until_epoch_and_recover: sleep to the API reset epoch, confirm the
    limit cleared via the API, then inject exactly once."""

    def _epoch_body(self, query_cmd, extra=""):
        return f'''
set -u
export CODEX_RL_SOURCE_FOR_TEST=1
export CODEX_RL_STATE_DIR="$1"
export CODEX_RL_QUERY_CMD="{query_cmd}"
source "{WATCHER}" dummy-pane
LOG="$1/watcher.log"
MARGIN=0
RESET_CONFIRM_INTERVAL=0
RESET_CONFIRM_MAX=3
is_codex_pane() {{ return 0; }}
is_working() {{ return 1; }}
inject_continue() {{ printf 'INJECTED\\n' >> "$LOG"; }}
{extra}
past=$(( $(date +%s) - 5 ))
wait_until_epoch_and_recover "$past" 300
'''

    def _run_epoch(self, query_cmd, extra=""):
        state_dir = tempfile.mkdtemp(prefix="codex-rl-epoch-")
        try:
            result = _run_bash(self._epoch_body(query_cmd, extra), [state_dir])
            log = (Path(state_dir) / "watcher.log")
            log_text = log.read_text() if log.exists() else ""
            return result, log_text
        finally:
            shutil.rmtree(state_dir, ignore_errors=True)

    def test_injects_after_api_confirms_cleared(self):
        result, log = self._run_epoch(
            "printf '%s\\n' RL_OK=1 RL_REACHED=0 RL_USED_PERCENT=2"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("API confirms limit cleared", log)
        self.assertIn("INJECTED", log)

    def test_proceeds_when_api_unavailable_on_confirm(self):
        # After the reset wait, if the confirm query fails we still inject
        # (we already waited the reported reset time).
        result, log = self._run_epoch("printf '%s\\n' RL_OK=0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("API unavailable on confirm", log)
        self.assertIn("INJECTED", log)

    def test_keeps_waiting_while_api_still_reached_then_injects(self):
        # Emit RL_REACHED=1 for the first RESET_CONFIRM_MAX polls; the loop
        # exhausts its confirmations and injects anyway (best-effort resume).
        result, log = self._run_epoch(
            "printf '%s\\n' RL_OK=1 RL_REACHED=1 RL_USED_PERCENT=100"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("API still reports limit reached", log)
        self.assertIn("INJECTED", log)

    def test_invalid_epoch_does_not_inject(self):
        result, log = self._run_epoch(
            "printf '%s\\n' RL_OK=1 RL_REACHED=0",
            extra='wait_until_epoch_and_recover "not-a-number" 300 || true\nexit 0',
        )
        # The extra invocation with a bad epoch must log + refuse to inject.
        self.assertIn("invalid reset epoch", log)


class HelperCompileTests(unittest.TestCase):
    def test_query_helper_compiles(self):
        result = subprocess.run(
            ["python3", "-m", "py_compile", str(QUERY_HELPER)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_hook_scripts_pass_bash_syntax_check(self):
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


if __name__ == "__main__":
    unittest.main()
