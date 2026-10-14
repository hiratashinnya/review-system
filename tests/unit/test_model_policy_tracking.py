"""無視対象 runtime の Git 追跡防止を一時リポジトリで検証する。"""

import subprocess
import tempfile
import unittest
from pathlib import Path

from model_policy.tracked_runtime import check_tracked_runtime


class RuntimeTrackingTests(unittest.TestCase):
    def test_ignored_runtime_is_allowed_but_force_added_runtime_stops(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q", temporary], check=True, capture_output=True)
            (root / ".gitignore").write_text(".github/agents/runtime-*.agent.md\n")
            runtime = root / ".github/agents/runtime-test.agent.md"
            runtime.parent.mkdir(parents=True)
            runtime.write_text("local resolved model\n")
            check_tracked_runtime(root)
            subprocess.run(["git", "add", "-f", str(runtime)], cwd=root, check=True, capture_output=True)
            with self.assertRaises(ValueError):
                check_tracked_runtime(root)

    def test_non_git_root_stops(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(subprocess.CalledProcessError):
                check_tracked_runtime(Path(temporary))
