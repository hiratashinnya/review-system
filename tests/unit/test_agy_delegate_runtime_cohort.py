"""通常runが実resolver/proof読取/OS adapterを通り、未知では起動しない。"""

import json
from unittest.mock import patch

from agy_delegate.runner import run
from agy_delegate.runtime import verify_runtime
from tests.unit.agy_runtime_cohort_fixture import RuntimeCohortFixture


class RuntimeCohortTests(RuntimeCohortFixture):
    def test_supported_snapshot_passes_real_runtime_and_normal_runner(self):
        with patch("subprocess.run", side_effect=self.boundary):
            self.assertEqual(verify_runtime(self.request), [])
            self.counts = dict.fromkeys(self.counts, 0)
            result = run(self.request)
        self.assertEqual(result.classification, "success_candidate", result.reasons)
        self.assertEqual(self.counts, {"os": 3, "version": 1, "model": 1})
        self.assertTrue((self.workspace / "launched.json").exists())

    def test_bad_proof_unknown_snapshot_extra_allow_ask_and_invalid_json_are_child_zero(self):
        global_file = self.files["global"]
        original = global_file.read_bytes()
        for payload in ('{', '{"permissions":{},"permissions":{}}',
                        '{"permissions":{"allow":["command(regex:.*)"]}}',
                        '{"permissions":{"ask":["write_file(private-rule-marker)"]}}'):
            with self.subTest(payload=payload):
                global_file.write_text(payload)
                with patch("subprocess.run", side_effect=self.boundary):
                    result = run(self.request)
                self.assertNotEqual(result.exit_code, 0)
                self.assertEqual(self.counts, {"os": 0, "version": 0, "model": 0})
                self.assertNotIn("private-rule-marker", repr(result.reasons))
                self.assertNotIn(str(self.profile), repr(result.reasons))
                self.assertEqual(global_file.read_text(), payload)
        global_file.write_bytes(original)
        self.files["shared"].write_text('{"userSettings":{"new_policy":true}}')
        with patch("subprocess.run", side_effect=self.boundary):
            self.assertNotEqual(run(self.request).exit_code, 0)
        self.assertEqual(self.counts["os"], 0)

    def test_unready_caller_and_logical_template_invalid_do_not_even_probe_os(self):
        self.settings.write_text('{}')
        with patch("subprocess.run", side_effect=self.boundary):
            self.assertNotEqual(run(self.request).exit_code, 0)
        self.assertEqual(sum(self.counts.values()), 0)

    def test_changes_after_version_prevent_prompt_and_do_not_mutate_bad_input(self):
        changed = '{"permissions":{"allow":["command(regex:.*)"]}}'
        self.after_version = lambda: self.files["global"].write_text(changed)
        with patch("subprocess.run", side_effect=self.boundary):
            result = run(self.request)
        self.assertNotEqual(result.exit_code, 0)
        self.assertEqual(self.counts["version"], 1)
        self.assertEqual(self.counts["model"], 0)
        self.assertEqual(self.files["global"].read_text(), changed)

    def test_windows_change_is_rejected_with_os_child_distinct_from_agy(self):
        self.after_os = lambda: self.files["project"].write_text('{"id":"changed"}')
        with patch("subprocess.run", side_effect=self.boundary):
            result = run(self.request)
        self.assertNotEqual(result.exit_code, 0)
        self.assertEqual(self.counts, {"os": 1, "version": 0, "model": 0})

    def test_valid_fingerprint_cannot_authorize_unobserved_native_command_allow(self):
        from agy_delegate.native_paths import native_workspace_path
        from agy_delegate.permission_rules import expected_path_rules
        rules = json.loads(self.files["global"].read_text())
        rules["permissions"]["allow"].append(expected_path_rules(native_workspace_path(self.workspace))["allow"][2])
        self.files["global"].write_text(json.dumps(rules))
        self.refresh_proof()
        with patch("subprocess.run", side_effect=self.boundary):
            result = run(self.request)
        self.assertIn("unreviewed_or_conflicting_rules:allow", result.reasons)
        self.assertEqual(sum(self.counts.values()), 0)
