"""Recursive sanitization and minimization regressions without a live API."""
import json
import os
import unittest
from unittest.mock import patch
from jev_hooks.outbound_evidence import outbound_evidence, outbound_questions
from jev_hooks.redaction import known_secrets, redact


class SafetyRedactionTests(unittest.TestCase):
    def test_nested_credentials_and_common_strings_are_removed(self):
        value = {"headers": {"Authorization": "header-canary", "Cookie": "cookie-canary"},
                 "nested": [{"password": "password-canary", "refresh_token": "token-canary"}],
                 "text": 'token="text-canary" password=word-canary '
                         'Authorization: Bearer bearer-canary '
                         'Basic YmFzaWMtY2FuYXJ5 '
                         '-----BEGIN RSA PRIVATE KEY-----\npem-canary\n'
                         '-----END RSA PRIVATE KEY-----',
                 "thinking": "private-reasoning-canary"}
        serialized = json.dumps(redact(value, ()))
        self.assertNotIn("canary", serialized)
        self.assertNotIn("YmFzaWM", serialized)

    def test_declared_values_are_read_without_environment_dump(self):
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "primary-canary",
                                     "MY_APP_SECRET": "declared-canary",
                                     "UNRELATED_ENV": "unrelated-canary"}, clear=True):
            with patch.object(os.environ, "items", side_effect=AssertionError("envdump")):
                values = known_secrets({"secret_env_vars": ["MY_APP_SECRET"]})
        self.assertEqual(set(values), {"primary-canary", "declared-canary"})
        self.assertEqual(redact("primary-canary/declared-canary", values),
                         "[REDACTED]/[REDACTED]")

    def test_sensitive_file_and_shell_results_are_omitted(self):
        evidence = {"current_turn_tool_ids": ["file", "shell", "safe"],
                    "tool_calls": {"file": {"name": "Read", "input": {"file_path": "/x/.env"}},
                                   "shell": {"name": "Bash", "input": {"command": "cat config"}},
                                   "safe": {"name": "WebSearch", "input": {"query": "safe query"}},
                                   "old": {"name": "Read", "input": {}}},
                    "tool_results": {key: {"content": value} for key, value in
                                     [("file", "unknown-file-canary"), ("shell", "unknown-shell-canary"),
                                      ("safe", "safe research"), ("old", "old-turn-canary")]},
                    "transcript_path": "unneeded-path-canary", "private": "private-canary"}
        result = outbound_evidence(evidence, ())
        self.assertNotIn("canary", json.dumps(result))
        self.assertEqual(result["tool_results"]["safe"]["content"], "safe research")

    def test_questions_keep_schema_keys_even_for_short_secrets(self):
        result = outbound_questions({"q": {"type": "choice", "instructions": "q secret",
                                  "criteria": {"yes": "q", "no": "no", "unknown": "q"}}}, ("q",))
        self.assertEqual(result["q"]["type"], "choice")
        self.assertEqual(set(result["q"]["criteria"]), {"yes", "no", "unknown"})
        self.assertNotIn("q", result["q"]["instructions"])

    def test_evidence_is_not_mutated_and_large_content_is_bounded(self):
        evidence = {"public_messages": ["token=canary", "x" * 9000], "history_complete": True}
        snapshot = json.dumps(evidence)
        result = outbound_evidence(evidence, ())
        self.assertEqual(json.dumps(evidence), snapshot)
        self.assertLess(len(result["public_messages"][1]), 8100)

    def test_secret_keys_drop_the_entry_without_renaming_collisions(self):
        evidence = {"current_tool_input": {"first-known": "first-value-canary",
                    "prefix-second-known": {"nested": "second-value-canary"},
                    "Authorization: Bearer credential-key-canary": "credential-value-canary",
                    "[REDACTED]": "ordinary", "safe": [{"token=label-canary": "label-value-canary"}]}}
        result = outbound_evidence(evidence, ("first-known", "second-known"))
        self.assertNotIn("canary", json.dumps(result))
        self.assertEqual(result["current_tool_input"], {"[REDACTED]": "ordinary", "safe": [{}]})

    def test_owned_evidence_schema_stays_distinct_from_arbitrary_keys(self):
        evidence = {"current_tool_input": {"name": "key-associated-canary"},
                    "tool_calls": {"call": {"name": "WebSearch", "input": {"query": "query value"}},
                                   "input": {"name": "Read", "input": {"path": "plain"}}},
                    "tool_results": {"call": {"content": "content value"}, "input": {"content": "id-value-canary"}}}
        result = outbound_evidence(evidence, ("current_tool_input", "name", "input", "query", "content"))
        self.assertEqual(result["current_tool_input"], {})
        self.assertEqual(set(result["tool_calls"]), {"call"})
        self.assertEqual(set(result["tool_calls"]["call"]), {"name", "input"})
        self.assertEqual(set(result["tool_calls"]["call"]["input"]), {"query"})
        self.assertEqual(set(result["tool_results"]["call"]), {"content", "is_error"})
        self.assertNotIn("canary", json.dumps(result))
