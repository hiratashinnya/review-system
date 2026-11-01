"""偽層だけを使う保守的許可監査。agy の実効 merge を実測しない。"""

import json
import unittest
from dataclasses import replace
from unittest.mock import patch

from agy_delegate.permissions import expected_rules
from agy_delegate.runtime import verify_runtime
from agy_delegate.settings_layer_types import SettingsLayer, SettingsResolution
from agy_delegate.settings_layers import inspect_layer_resolution
from tests.unit.agy_delegate_fixtures import FakeWorkspace


def fixture_permissions(data):
    """fixture 固有 schema。実際の project/shared/admin schema ではない。"""
    if set(data) != {"fixture_permissions"}:
        raise ValueError("fixture_schema_invalid")
    return data["fixture_permissions"]


class SettingsLayersTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeWorkspace()
        self.addCleanup(self.fake.close)
        self.rules = expected_rules(self.fake.workspace)
        self.layers = []
        for name in ("global", "project", "shared_user", "admin"):
            path = self.fake.workspace / f"fake-{name}.json"
            rules = self.rules if name == "global" else {key: [] for key in self.rules}
            path.write_text(json.dumps({"fixture_permissions": rules}))
            self.layers.append(SettingsLayer(name, path, fixture_permissions))

    def inspect(self, layers=None, reasons=()):
        return inspect_layer_resolution(SettingsResolution(tuple(self.layers if layers is None else layers),
                                                           reasons), self.fake.workspace)

    def write(self, index, rules):
        self.layers[index].path.write_text(json.dumps({"fixture_permissions": rules}))

    def test_all_layers_read_only_audit_and_runtime_merge_still_unverified(self):
        before = [layer.path.read_bytes() for layer in self.layers]
        self.assertEqual(self.inspect(), [])
        self.assertEqual([layer.path.read_bytes() for layer in self.layers], before)
        with patch("agy_delegate.runtime.resolve_settings_layers",
                   return_value=SettingsResolution(tuple(self.layers))), patch("subprocess.run") as child:
            reasons = verify_runtime(self.fake.request())
        child.assert_not_called()
        self.assertTrue(any(reason.startswith("cohort_") for reason in reasons))

    def test_project_allow_does_not_erase_global_deny_or_shared_ask(self):
        self.write(1, self.rules)
        self.write(2, {"allow": [], "ask": [self.rules["allow"][0]], "deny": []})
        self.assertIn("unreviewed_or_conflicting_rules:ask", self.inspect())
        self.write(2, {"allow": [], "ask": [], "deny": [self.rules["allow"][1]]})
        self.assertIn("unreviewed_or_conflicting_rules:deny", self.inspect())

    def test_unknown_inventory_schema_and_invalid_layer_stop(self):
        self.assertIn("settings_layer_inventory_incomplete", self.inspect(self.layers[:-1]))
        layers = list(self.layers)
        layers[1] = replace(layers[1], path=None)
        self.assertIn("settings_layer_path_unidentified:project", self.inspect(layers))
        layers[1] = replace(self.layers[1], decode_permissions=None)
        self.assertIn("settings_layer_schema_unverified:project", self.inspect(layers))
        self.layers[2].path.write_text('{"fixture_permissions":{}}')
        self.assertIn("settings_layer_permission_shape_invalid:shared_user", self.inspect())

    def test_absent_admin_differs_from_unreadable_and_reappearing_admin(self):
        self.layers[3].path.unlink()
        self.assertIn("settings_layer_unreadable:admin", self.inspect())
        self.layers[3] = replace(self.layers[3], absent=True)
        self.assertEqual(self.inspect(), [])
        with patch("pathlib.Path.lstat", side_effect=PermissionError("private path")):
            self.assertIn("settings_layer_unreadable:admin", self.inspect())
        self.layers[3].path.write_text('{}')
        self.assertIn("settings_layer_absence_mismatch:admin", self.inspect())

    def test_missing_corpus_broad_rules_invalid_json_and_merge_reason_stop(self):
        self.write(0, self.rules | {"deny": []})
        self.assertIn("missing_rules:deny", self.inspect())
        self.write(0, self.rules)
        self.write(1, {"allow": ["command(regex:.*)"], "ask": [], "deny": []})
        self.assertIn("unreviewed_or_conflicting_rules:allow", self.inspect())
        self.layers[1].path.write_text('{')
        self.assertIn("settings_layer_unreadable_or_invalid:project", self.inspect())
        self.assertIn("settings_permission_merge_unverified",
                      self.inspect(reasons=("settings_permission_merge_unverified",)))
