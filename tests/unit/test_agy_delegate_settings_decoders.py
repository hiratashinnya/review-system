"""公式global optional schemaの明示ruleと不正群の境界。"""

import unittest

from agy_delegate.settings_decoders import decode_global_permissions


class GlobalPermissionsDecoderTests(unittest.TestCase):
    def test_optional_groups_are_explicit_rule_absence_with_omission_provenance(self):
        decoded = decode_global_permissions({"permissions": {"allow": ["read_file(W)"]},
                                             "unrelated_future_setting": {"private": True}})
        self.assertEqual(decoded.rules, {"allow": ["read_file(W)"], "ask": [], "deny": []})
        self.assertEqual(decoded.omitted, ("ask", "deny"))
        self.assertEqual(decoded.missing, ())
        self.assertEqual(decode_global_permissions({}).omitted, ("allow", "ask", "deny"))

    def test_unknown_permission_members_and_nonobject_roots_are_rejected(self):
        for value in ([], None, {"permissions": None}, {"permissions": []},
                      {"permissions": {"future_admin_rule": []}}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                decode_global_permissions(value)

    def test_invalid_group_does_not_discard_valid_groups(self):
        for invalid in (None, False, "read_file(W)", [1], ["unknown(W)"],
                        ["write_file(W)\n"], ["command(W)\nwrite_file(W)"]):
            with self.subTest(invalid=invalid):
                decoded = decode_global_permissions({"permissions": {
                    "allow": ["read_file(W)"], "ask": invalid, "deny": ["write_file(W/corpus)"]}})
                self.assertEqual(decoded.invalid, ("ask",))
                self.assertEqual(decoded.rules["allow"], ["read_file(W)"])
                self.assertEqual(decoded.rules["deny"], ["write_file(W/corpus)"])

