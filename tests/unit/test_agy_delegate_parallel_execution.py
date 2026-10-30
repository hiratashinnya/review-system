"""同root非重複子の同時性と祖先重複の全件未起動。"""

import json
import threading
import time
import unittest
from dataclasses import replace
from unittest.mock import patch

from agy_delegate.permissions import expected_rules
from agy_delegate.runner import run, run_parallel
from agy_delegate.types import Result
from tests.unit.agy_delegate_fixtures import FakeWorkspace, run_synthetic, synthetic_success


class ParallelExecutionTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeWorkspace()
        self.addCleanup(self.fake.close)
        self.root = self.fake.workspace
        self.children = (self.root / "a", self.root / "b")
        for child in self.children:
            child.mkdir()
        rules = expected_rules(self.root)
        rules["deny"].extend(f"write_file({path}/doc-system-v2/nodes)" for path in self.children)
        self.fake.settings.write_text(json.dumps({"permissions": rules}))
        self.requests = [replace(self.fake.request(), workspace=child, permission_root=self.root)
                         for child in self.children]

    def test_ancestor_overlap_rejects_all_before_pool_execution(self):
        for requests in ([self.fake.request(), self.requests[0]], [self.requests[0], self.fake.request()]):
            with patch("agy_delegate.runner._run") as run_one:
                with self.assertRaisesRegex(ValueError, "^parallel_workspace_overlap$"):
                    run_parallel(requests, max_concurrency=2)
            run_one.assert_not_called()

    def test_disjoint_children_overlap_in_execute_and_keep_order_records(self):
        barrier = threading.Barrier(2)
        lifetimes = {}
        def execute(request, run_id):
            start = time.monotonic()
            barrier.wait(timeout=3)
            time.sleep(0.02)
            lifetimes[request.workspace] = (start, time.monotonic())
            return Result(run_id, classification="success_candidate", status="SUCCESS", agy_exit_code=0,
                          conversation_id=request.workspace.name)
        with patch("agy_delegate.runner.verify_runtime", return_value=[]), \
                patch("agy_delegate.runner.execute", side_effect=execute):
            results = run_parallel(self.requests, max_concurrency=2)
        self.assertEqual([result.conversation_id for result in results], ["a", "b"])
        self.assertTrue(all(result.exit_code == 0 for result in results))
        self.assertNotEqual(results[0].run_id, results[1].run_id)
        self.assertLess(max(value[0] for value in lifetimes.values()), min(value[1] for value in lifetimes.values()))
        self.assertTrue(all((request.workspace / "tmp/agy" / result.run_id / "result.json").is_file()
                            for request, result in zip(self.requests, results)))

    def test_continuation_rejects_root_change_and_legacy_summary(self):
        request = self.requests[0]
        self.assertEqual(run_synthetic(request).exit_code, 0)
        path = request.workspace / "tmp/agy/conversation-conversation-1.json"
        original = json.loads(path.read_text())
        before = (request.workspace / "launch-count.txt").read_text()
        for data, reason in [(original | {"permission_root": str(request.workspace)}, "conversation_permission_root_mismatch"),
                             ({key: value for key, value in original.items() if key != "permission_root"}, "conversation_record_missing_or_invalid")]:
            path.write_text(json.dumps(data))
            result = run_synthetic(replace(request, conversation="conversation-1"))
            self.assertIn(reason, result.reasons)
        self.assertEqual((request.workspace / "launch-count.txt").read_text(), before)
