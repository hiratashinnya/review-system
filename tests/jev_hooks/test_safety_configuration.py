"""Missing credentials are configuration failures rather than unknown answers."""
import contextlib
import io
import json
import os
import unittest
from unittest.mock import patch
from jev_hooks import __main__
from jev_hooks.configuration_failure import ConfigurationFault, configuration_failure
from jev_hooks.evaluator import JevEvaluator


class SafetyConfigurationTests(unittest.TestCase):
    def test_missing_key_enforces_stop_and_pretool_and_shadow_passes(self):
        with patch.dict(os.environ, {}, clear=True):
            for kind in ("Stop", "PreToolUse"):
                event = {"hook_event_name": kind, "stop_hook_active": True}
                decision, fault = configuration_failure(event, {"evaluator": "jev", "mode": "enforce"})
                self.assertEqual(fault, "missing_api_key")
                self.assertTrue(decision)
                if kind == "Stop":
                    self.assertEqual(decision["decision"], "block")
                else:
                    self.assertEqual(decision["hookSpecificOutput"]["permissionDecision"], "deny")
                self.assertEqual(configuration_failure(event, {"evaluator": "jev", "mode": "shadow"}),
                                 ({}, "missing_api_key"))
                self.assertEqual(configuration_failure(event, {"evaluator": "mock", "mode": "enforce"}),
                                 ({}, None))

    def test_direct_evaluation_preserves_typed_configuration_fault(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigurationFault):
                JevEvaluator({}).evaluate({}, ["r1_waiting_for_answer"])
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "  "}, clear=True):
            with self.assertRaises(ConfigurationFault):
                JevEvaluator({}).evaluate({}, ["r1_waiting_for_answer"])
        for name in (None, [], ""):
            with self.assertRaises(ConfigurationFault):
                JevEvaluator({"api_key_env": name}).evaluate({}, ["r1_waiting_for_answer"])

    def test_main_does_not_turn_configuration_failure_into_pass(self):
        for kind in ("Stop", "PreToolUse"):
            event = {"hook_event_name": kind}
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch("sys.argv", ["jev_hooks"]), patch("sys.stdin", io.StringIO(json.dumps(event))):
                with patch.object(__main__, "load_config", return_value={"evaluator": "jev", "mode": "enforce"}):
                    with patch.object(__main__, "run_event", side_effect=ConfigurationFault("private-canary")):
                        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                            __main__.main()
            self.assertTrue(json.loads(stdout.getvalue()))
            self.assertNotIn("private-canary", stdout.getvalue() + stderr.getvalue())

    def test_missing_key_survives_storage_failure_in_general_catch(self):
        for kind in ("Stop", "PreToolUse"):
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch.dict(os.environ, {}, clear=True), patch("sys.argv", ["jev_hooks"]):
                with patch("sys.stdin", io.StringIO(json.dumps({"hook_event_name": kind}))):
                    with patch.object(__main__, "load_config", return_value={"evaluator": "jev", "mode": "enforce"}):
                        with patch.object(__main__, "run_event", side_effect=OSError("private-canary")):
                            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                                __main__.main()
            self.assertTrue(json.loads(stdout.getvalue()))
            self.assertNotIn("private-canary", stdout.getvalue() + stderr.getvalue())
