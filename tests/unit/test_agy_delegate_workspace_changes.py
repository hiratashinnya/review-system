"""git不要の前後差分と観測不能の明示。"""

import json
import unittest
from unittest.mock import patch

from agy_delegate.runner import run
from agy_delegate.workspace_changes import snapshot, changes
from tests.unit.agy_delegate_fixtures import FakeWorkspace, run_synthetic


class WorkspaceChangesTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeWorkspace()
        self.addCleanup(self.fake.close)

    def test_added_modified_deleted_and_exclusions(self):
        workspace = self.fake.workspace
        (workspace / "deleted").write_text("old")
        (workspace / "modified").write_text("old")
        (workspace / "linked").symlink_to(workspace / "modified")
        before = snapshot(workspace)
        (workspace / "deleted").unlink()
        (workspace / "modified").write_text("new")
        (workspace / "added").write_text("new")
        (workspace / "tmp/agy").mkdir(parents=True)
        (workspace / "tmp/agy/record").write_text("ignored")
        (workspace / ".git").mkdir()
        (workspace / ".git/index").write_text("ignored")
        self.assertEqual(changes(before, snapshot(workspace)), [
            {"path": "added", "change": "added"}, {"path": "deleted", "change": "deleted"},
            {"path": "modified", "change": "modified"}])

    def test_execution_returns_changes_and_attribution_limit(self):
        result = run_synthetic(self.fake.request())
        self.assertIn({"path": "launched.json", "change": "added"}, result.workspace_changes)
        self.assertIn("concurrent_actor_changes_not_attributable_to_agy", result.workspace_change_limitations)
        record = self.fake.workspace / "tmp/agy" / result.run_id / "result.json"
        self.assertEqual(json.loads(record.read_text())["workspace_changes"], result.workspace_changes)

    def test_after_snapshot_failure_is_not_reported_as_no_changes(self):
        with patch("agy_delegate.runner.snapshot", side_effect=[{}, ValueError("workspace_snapshot_incomplete")]):
            result = run_synthetic(self.fake.request())
        self.assertIn("workspace_snapshot_incomplete", result.reasons)
        self.assertIn("observation_incomplete", result.workspace_change_limitations)
        self.assertEqual(result.classification, "failed")

    def test_unstarted_execution_explicitly_reports_observation_not_performed(self):
        result = run(self.fake.request())
        self.assertIn("observation_not_performed", result.workspace_change_limitations)
