"""許可rootの包含・literal追加deny・raw templateの境界。"""

import json
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from agy_delegate.logical_settings import read_logical_settings
from agy_delegate.native_policy import expected_file_only_rules
from agy_delegate.permission_paths import checked_directory, effective_permission_root
from agy_delegate.permissions import expected_rules, inspect_settings
from agy_delegate.request_policy import policy_snapshot, request_path_binding
from agy_delegate.runner import run
from tests.unit.agy_delegate_fixtures import FakeWorkspace


class PermissionRootTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeWorkspace()
        self.addCleanup(self.fake.close)
        self.root = self.fake.workspace
        self.a, self.b = self.root / "a", self.root / "b"
        self.a.mkdir()
        self.b.mkdir()

    def shared_rules(self):
        rules = expected_rules(self.root)
        rules["deny"].extend(f"write_file({path}/doc-system-v2/nodes)" for path in (self.a, self.b))
        self.fake.settings.write_text(json.dumps({"permissions": rules}))
        return rules

    def test_omitted_and_explicit_same_root_preserve_binding(self):
        request = self.fake.request()
        with patch.dict("os.environ", {"WSL_DISTRO_NAME": "Synthetic"}):
            self.assertEqual(request_path_binding(request), request_path_binding(replace(request, permission_root=self.root)))
        self.assertEqual(effective_permission_root(self.root), self.root)
        self.assertEqual(policy_snapshot(request)[2], (self.root,))

    def test_child_shared_deny_template_and_native_profile_are_bounded(self):
        self.shared_rules()
        request = replace(self.fake.request(), workspace=self.a, permission_root=self.root)
        root, _, roots = policy_snapshot(request)
        self.assertEqual(roots, (self.root, self.a, self.b))
        self.assertEqual(inspect_settings(request.settings, root), [])
        with patch.dict("os.environ", {"WSL_DISTRO_NAME": "Synthetic"}):
            native = expected_file_only_rules(root, corpus_roots=roots)
        self.assertEqual([len(native[group]) for group in ("allow", "ask", "deny")], [2, 0, 4])
        self.assertEqual(native["deny"][-1], "command(regex:.*)")

    def test_root_outside_missing_alias_and_dotdot_fail_before_any_child(self):
        alias = self.root / "alias"
        alias.symlink_to(self.a, target_is_directory=True)
        requests = [replace(self.fake.request(), permission_root=self.a),
                    replace(self.fake.request(), workspace=alias),
                    replace(self.fake.request(), permission_root=self.root / "missing"),
                    replace(self.fake.request(), workspace=self.a / "..")]
        with patch("subprocess.run") as child:
            for request in requests:
                self.assertTrue(run(request).reasons)
        child.assert_not_called()
        with self.assertRaises(ValueError):
            checked_directory(Path("relative"))

    def test_extra_deny_unknown_syntax_outside_and_duplicate_are_rejected(self):
        rules = self.shared_rules()
        extras = ["command(regex:.*)", f"write_file({self.root}/a/../b/doc-system-v2/nodes)",
                  f"write_file({self.a}//doc-system-v2/nodes)", "write_file(/tmp/doc-system-v2/nodes)",
                  f"write_file({self.a}/doc-system-v2/nodes/**)", rules["deny"][0]]
        for extra in extras:
            with self.subTest(extra=extra):
                self.fake.settings.write_text(json.dumps({"permissions": rules | {"deny": rules["deny"] + [extra]}}))
                self.assertTrue(inspect_settings(self.fake.settings, self.root))

    def test_raw_bytes_changes_hash_without_reinterpreting_template(self):
        first = read_logical_settings(self.fake.settings, self.root)
        self.fake.settings.write_bytes(self.fake.settings.read_bytes() + b"\n")
        second = read_logical_settings(self.fake.settings, self.root)
        self.assertNotEqual(first[0], second[0])
        self.assertEqual(first[1], second[1])

    def test_child_corpus_deny_and_root_corpus_deny_are_required(self):
        request = replace(self.fake.request(), workspace=self.a, permission_root=self.root)
        with self.assertRaisesRegex(ValueError, "^permission_workspace_corpus_deny_missing$"):
            policy_snapshot(request)
        self.fake.settings.write_text(json.dumps({"permissions": expected_rules(self.a)}))
        self.assertTrue(inspect_settings(self.fake.settings, self.root))
