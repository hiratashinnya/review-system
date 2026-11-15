"""Issue #722: deep JSON must not bypass the SubagentStop fail-close gate."""

import io
import json

from issue_start import subagent_hooks
from tests.unit.test_subagent_hooks import HookTestCase


class ActivePointerRecursionRegressionTests(HookTestCase):
    def test_deep_pointer_blocks_on_first_stop_without_running_karte(self):
        self.write_active("[" * 100000)
        rc = subagent_hooks.run_stop(
            stdin=self.stdin({"agent_type": "issue-fixer"}),
            stdout=self.stdout,
            stderr=self.stderr,
            cwd=self.root,
            runner=self.runner(),
        )
        self.assertEqual(rc, 0)
        decision = json.loads(self.stdout.getvalue())
        self.assertEqual(decision["decision"], "block")
        self.assertIn("判定不能は fail-close", decision["reason"])
        self.assertIn("ACTIVE_POINTER_UNREADABLE", self.stderr.getvalue())
        self.assertEqual(self.runner_calls, [])

    def test_deep_pointer_still_allows_reentrant_stop(self):
        self.write_active("[" * 100000)
        rc = subagent_hooks.run_stop(
            stdin=self.stdin({
                "agent_type": "issue-fixer",
                "stop_hook_active": True,
            }),
            stdout=self.stdout,
            stderr=self.stderr,
            cwd=self.root,
            runner=self.runner(),
        )
        self.assertEqual(rc, 0)
        self.assertSilentAllow()
        self.assertIn("STOP_HOOK_REENTRY", self.stderr.getvalue())
        self.assertEqual(self.runner_calls, [])

    def test_deep_stdin_payload_is_out_of_scope_without_traceback(self):
        rc = subagent_hooks.run_stop(
            stdin=io.StringIO("[" * 100000),
            stdout=self.stdout,
            stderr=self.stderr,
            cwd=self.root,
            runner=self.runner(),
        )
        self.assertEqual(rc, 0)
        self.assertSilentAllow()
        self.assertIn('"result":"skip"', self.stderr.getvalue())
        self.assertEqual(self.runner_calls, [])
