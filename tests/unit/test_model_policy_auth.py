"""認証方式別の候補選択と、秘密を出力しないSTOPを検証する。"""

import json
import contextlib
import io
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from model_policy.catalog import codex_catalog
from model_policy.codex_auth import codex_auth_mode
from model_policy.policy import load_policy
from model_policy.resolver import resolve_models
from tests.unit.test_model_policy_resolver import candidate


class CodexAuthTests(unittest.TestCase):
    def test_auth_mode_identification_does_not_expose_credentials(self):
        for status, expected in (("Logged in using ChatGPT", "backend"),
                                 ("Logged in using an API key - redacted-dummy", "api"),
                                 ("Logged in using API key - redacted-dummy", "api")):
            runner = Mock(return_value=SimpleNamespace(stdout="", stderr=status))
            with contextlib.redirect_stdout(io.StringIO()) as output, \
                    contextlib.redirect_stderr(io.StringIO()) as errors:
                self.assertEqual(codex_auth_mode(runner), expected)
            self.assertNotIn("redacted-dummy", output.getvalue() + errors.getvalue())
            runner.assert_called_once_with(["codex", "login", "status"], capture_output=True,
                                           text=True, check=True, timeout=10)
        runner = Mock(side_effect=subprocess.CalledProcessError(1, "codex", stderr="secret"))
        with self.assertRaises(ValueError) as failure:
            codex_auth_mode(runner)
        self.assertNotIn("secret", str(failure.exception))

    def test_new_backend_minor_is_selected_while_api_excludes_it(self):
        policy = load_policy()
        selectors = policy["platforms"]["codex"]["families"]
        models = [{"slug": candidate(s, minor), "visibility": "list", "supported_in_api": available}
                  for s in selectors.values() for minor, available in ((".1", True), (".2", False))]
        runner = Mock(return_value=SimpleNamespace(stdout=json.dumps({"models": models}), stderr=""))
        for mode, minor in (("backend", ".2"), ("api", ".1")):
            resolved = resolve_models(policy, "codex", codex_catalog(runner, auth_mode=mode))
            expected = {tier: candidate(selectors[family], minor)
                        for tier, family in policy["platforms"]["codex"]["tiers"].items()}
            self.assertEqual(resolved, expected)
        with self.assertRaises(ValueError):
            codex_catalog(runner, auth_mode="unknown")
        with self.assertRaises(ValueError):
            codex_auth_mode(Mock(return_value=SimpleNamespace(stdout="Not logged in", stderr="")))
