"""許可欠落、deny/ask競合、広い command、危険入力を検査する。"""

import json
import re
import unittest

from agy_delegate.permissions import expected_rules, inspect_settings
from tests.unit.agy_delegate_fixtures import FakeWorkspace


class PermissionTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeWorkspace()
        self.addCleanup(self.fake.close)

    def test_japanese_space_and_settings_unchanged(self):
        before = self.fake.settings.read_bytes()
        self.assertEqual(inspect_settings(self.fake.settings, self.fake.workspace), [])
        self.assertEqual(self.fake.settings.read_bytes(), before)

    def test_missing_rules_conflicting_groups_and_unknown_layers(self):
        for group in ("allow", "deny", "ask"):
            rules = expected_rules(self.fake.workspace)
            rules[group] = [] if rules[group] else [rules["allow"][0]]
            self.fake.settings.write_text(json.dumps({"permissions": rules}))
            self.assertTrue(inspect_settings(self.fake.settings, self.fake.workspace))
        self.fake.settings.write_text(json.dumps({"permissions": expected_rules(self.fake.workspace),
                                                  "project": {}}))
        self.assertTrue(inspect_settings(self.fake.settings, self.fake.workspace))

    def test_command_template_rejects_compounds_and_partial_expressions(self):
        rules = expected_rules(self.fake.workspace)
        pattern = rules["allow"][-1][len("command(regex:"):-1]
        command = "Get-ChildItem -Name '" + str(self.fake.workspace.resolve()) + "'"
        self.assertIsNotNone(re.search(pattern, command))
        for suffix in ("; echo bad", " | echo bad", " > out", " & echo bad", " $(x)", "`x`", "\n", " extra"):
            self.assertIsNone(re.search(pattern, command + suffix), suffix)
        self.assertIsNone(re.search(pattern, "prefix " + command))

    def test_extra_broad_command_and_corpus_glob_fail(self):
        rules = expected_rules(self.fake.workspace)
        for extra in ("command(regex:.*)", "command(Get-ChildItem)", "write_file(/)"):
            changed = {key: list(value) for key, value in rules.items()}
            changed["allow"].append(extra)
            self.fake.settings.write_text(json.dumps({"permissions": changed}))
            self.assertTrue(inspect_settings(self.fake.settings, self.fake.workspace))
        rules["deny"][0] += "/**"
        self.fake.settings.write_text(json.dumps({"permissions": rules}))
        self.assertTrue(inspect_settings(self.fake.settings, self.fake.workspace))

    def test_invalid_settings_types_and_unsafe_path(self):
        for data in ([], {"permissions": []}, {"permissions": {"allow": None, "deny": [], "ask": []}}):
            self.fake.settings.write_text(json.dumps(data))
            self.assertTrue(inspect_settings(self.fake.settings, self.fake.workspace))
        for name in ("semi;colon", "tick`", "line\n", "quote'", "part$(x)"):
            with self.assertRaises(ValueError):
                expected_rules(self.fake.workspace / name)


if __name__ == "__main__":
    unittest.main()
