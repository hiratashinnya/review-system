"""fake 子プロセス経由の起動禁止、失敗、継続、並列、画像差分。"""

import json
import subprocess
import unittest
from dataclasses import replace
from unittest.mock import patch

from agy_delegate.records import state_root
from agy_delegate.runner import run, run_parallel
from tests.unit.agy_delegate_fixtures import FakeWorkspace, run_synthetic, synthetic_runtime, synthetic_success


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeWorkspace()
        self.addCleanup(self.fake.close)

    def execute(self, request):
        return run_synthetic(request)

    def test_production_unverified_never_launches(self):
        result = run(self.fake.request())
        self.assertIn("settings_permission_merge_unverified", result.reasons)
        self.assertFalse((self.fake.workspace / "launched.json").exists())

    def test_bad_permissions_stopped_caller_and_bad_environment_never_launch(self):
        request = self.fake.request()
        cases = [replace(request, caller_state="stopped"), replace(request, print_timeout=0),
                 replace(request, executable=self.fake.workspace / "missing")]
        for candidate in cases:
            self.assertNotEqual(self.execute(candidate).exit_code, 0)
        self.fake.settings.write_text("{}")
        self.assertNotEqual(self.execute(request).exit_code, 0)
        self.assertFalse((self.fake.workspace / "launched.json").exists())

    def test_fake_denied_error_timeout_invalid_json_and_partial_response(self):
        variants = [dict(output=synthetic_success() | {"denied_actions": [{"action": "command", "display_name": "RunCommand"}]}),
                    dict(output=synthetic_success() | {"status": "ERROR"}),
                    dict(output=synthetic_success(), stderr="[agy] print timeout"),
                    dict(stdout="{"), dict(output=synthetic_success(), exit=4)]
        for data in variants:
            result = self.execute(replace(self.fake.request(), prompt=json.dumps(data)))
            self.assertNotEqual(result.exit_code, 0)
            self.assertEqual(result.classification != "success_candidate", result.exit_code != 0)
        launches = (self.fake.workspace / "launch-count.txt").read_text().splitlines()
        self.assertEqual(len(launches), len(variants))

    def test_outer_timeout_preserves_partial_output(self):
        timeout = subprocess.TimeoutExpired(["fake"], 1,
                                             output=json.dumps(synthetic_success()).encode())
        with patch("agy_delegate.process.verified_version", return_value="1.3.3"), patch("agy_delegate.process.subprocess.run", side_effect=timeout):
            result = self.execute(self.fake.request())
        self.assertTrue(result.truncated)
        self.assertIn("process_timeout", result.reasons)
        self.assertEqual(result.response, "result")
        self.assertNotEqual(result.exit_code, 0)

    def test_flags_precede_prompt_and_cwd_is_explicit(self):
        result = self.execute(self.fake.request())
        self.assertEqual(result.exit_code, 0)
        argv = json.loads((self.fake.workspace / "launched.json").read_text())
        self.assertLess(argv.index("--output-format"), argv.index("-p"))
        self.assertLess(argv.index("--print-timeout"), argv.index("-p"))
        self.assertNotIn("--dangerously-skip-permissions", argv)

    def test_continuation_failure_blocks_previous_success(self):
        self.assertEqual(self.execute(self.fake.request()).exit_code, 0)
        continued = self.fake.request(synthetic_success() | {"denied_actions": [{"action": "command", "display_name": "RunCommand"}]},
                                      conversation="conversation-1")
        self.assertNotEqual(self.execute(continued).exit_code, 0)
        blocked = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertIn("conversation_previous_failure", blocked.reasons)
        unknown = self.execute(self.fake.request(conversation="unknown"))
        self.assertIn("conversation_record_missing_or_invalid", unknown.reasons)

    def test_workspace_record_mismatch_and_lock_fail_closed(self):
        self.execute(self.fake.request())
        root = state_root(self.fake.workspace)
        record = root / "conversation-conversation-1.json"
        data = json.loads(record.read_text())
        data["workspace"] = "/different"
        record.write_text(json.dumps(data))
        self.assertIn("conversation_workspace_mismatch", self.execute(
            self.fake.request(conversation="conversation-1")).reasons)
        (root / "workspace.lock").mkdir()
        self.assertIn("workspace_lock_timeout", self.execute(self.fake.request()).reasons)

    def test_child_io_failure_releases_lock(self):
        with patch("agy_delegate.runner.execute", side_effect=OSError("private path")):
            result = self.execute(self.fake.request())
        self.assertIn("execution_io_error", result.reasons)
        self.assertFalse((state_root(self.fake.workspace) / "workspace.lock").exists())

    def test_exception_and_mismatched_return_block_continuation(self):
        self.execute(self.fake.request())
        with patch("agy_delegate.runner.execute", side_effect=OSError("failure")):
            self.execute(self.fake.request(conversation="conversation-1"))
        blocked = self.execute(self.fake.request(conversation="conversation-1"))
        self.assertIn("conversation_previous_failure", blocked.reasons)
        new = self.fake.request(synthetic_success("new"))
        self.assertEqual(self.execute(new).exit_code, 0)
        changed = self.execute(self.fake.request(synthetic_success("changed"), conversation="new"))
        self.assertIn("conversation_return_mismatch", changed.reasons)

    def test_parallel_results_are_separate_and_failures_not_hidden(self):
        other = FakeWorkspace()
        self.addCleanup(other.close)
        requests = [self.fake.request(), other.request(synthetic_success("other") | {"status": "ERROR"})]
        with patch("agy_delegate.runner.verify_runtime", synthetic_runtime):
            results = run_parallel(requests, max_concurrency=2)
        self.assertEqual([r.exit_code for r in results], [0, 1])
        self.assertNotEqual(results[0].run_id, results[1].run_id)
        with self.assertRaises(ValueError):
            run_parallel(requests, max_concurrency=0)

    def test_new_image_collection_and_continuation_ignore_old_image(self):
        image = self.fake.brain / "conversation-1" / "new.jpg"
        payload = dict(output=synthetic_success(), image=str(image))
        request = replace(self.fake.request(images=True, brain=self.fake.brain), prompt=json.dumps(payload))
        first = self.execute(request)
        self.assertEqual(first.exit_code, 0)
        self.assertEqual(len(first.artifacts), 1)
        second = self.execute(self.fake.request(conversation="conversation-1", images=True, brain=self.fake.brain))
        self.assertIn("image_missing", second.reasons)
        self.assertNotEqual(second.exit_code, 0)

    def test_failure_images_are_diagnostic_only(self):
        image = self.fake.brain / "conversation-1" / "new.jpg"
        payload = dict(output=synthetic_success() | {"status": "ERROR"}, image=str(image))
        result = self.execute(replace(self.fake.request(images=True, brain=self.fake.brain),
                                      prompt=json.dumps(payload)))
        self.assertEqual(len(result.artifacts), 1)
        self.assertEqual(result.classification != "success_candidate", result.exit_code != 0)
        self.assertNotEqual(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
