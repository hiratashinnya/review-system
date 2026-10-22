"""同workspace順次完走と先行timeoutに連動する待機予算。"""

import io
import json
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from unittest.mock import patch

from agy_delegate.cli import main
from agy_delegate.runner import run_parallel
from agy_delegate.types import Result
from tests.unit.agy_delegate_fixtures import FakeWorkspace, synthetic_success


class WorkspaceBatchTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeWorkspace()
        self.addCleanup(self.fake.close)

    def test_two_prompts_longer_than_ten_seconds_finish_through_cli(self):
        executable = self.fake.executable
        executable.write_text(executable.read_text().replace(
            "data = json.loads", "import time\ntime.sleep(10.1)\ndata = json.loads"))
        prompts = [json.dumps({"output": synthetic_success(identity)}) for identity in ("first", "second")]
        args = ["run", "--workspace", str(self.fake.workspace), "--settings", str(self.fake.settings),
                "--executable", str(executable), "--print-timeout", "12", "--caller-state", "ready",
                "--max-concurrency", "2", "--prompt", prompts[0], "--prompt", prompts[1]]
        output = io.StringIO()
        with patch("agy_delegate.runner.verify_runtime", return_value=[]), redirect_stdout(output):
            self.assertEqual(main(args), 0)
        results = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual([result["conversation_id"] for result in results], ["first", "second"])
        self.assertTrue(all(result["classification"] == "success_candidate" for result in results))
        self.assertTrue(all("workspace_lock_timeout" not in result["reasons"] for result in results))

    def test_wait_budget_sums_each_preceding_timeout(self):
        requests = [replace(self.fake.request(), print_timeout=timeout) for timeout in (12, 30, 5)]
        with patch("agy_delegate.runner._run", return_value=Result("run")) as run:
            run_parallel(requests, max_concurrency=2)
        self.assertEqual([call.args[1] for call in run.call_args_list], [22, 62, 77])
