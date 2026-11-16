"""G-03 contracts: sweep gating, owner boundary, and per-entry isolation."""

import inspect
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from gitgate import worktree
from gitgate.worktree_models import SweepEntryOutcome
from gitgate.worktree_sweep import run_sweep
from gitgate.worktree_sweep_handoff import _own_handoff
from gitgate.worktree_sweep_discard import _is_discardable
from gitgate.worktree_sweep_state import sweep_preflight


class SweepG03FacadeTests(unittest.TestCase):
    def test_compatibility_exports_and_signature(self):
        self.assertIs(worktree._own_handoff, _own_handoff)
        self.assertIs(worktree._is_discardable, _is_discardable)
        self.assertEqual(
            list(inspect.signature(worktree.sweep_abandoned_running).parameters),
            ["repo_root", "now", "reason", "no_live_dispatch", "runner"],
        )
        self.assertTrue(callable(worktree.worktree_forget))

    def test_no_idle_observation_does_not_read_ledger_or_git(self):
        with patch("gitgate.worktree_sweep._entries") as entries:
            with patch("gitgate.worktree_sweep._locked_worktree_paths") as locks:
                result = worktree.sweep_abandoned_running(
                    ".", now="fixed", reason="x", no_live_dispatch=False,
                )
        self.assertEqual(result, [])
        entries.assert_not_called()
        locks.assert_not_called()

    def test_locked_entry_is_not_marked_or_collected(self):
        with tempfile.TemporaryDirectory() as temp:
            relative = ".claude/worktrees/agent-test"
            entry = {"entry_id": "wl-123", "worktree_path": relative}
            locked = {str((Path(temp) / relative).resolve())}
            with patch("gitgate.worktree_sweep_state._mark") as mark:
                handoff, how, outcome = sweep_preflight(
                    temp, entry, now="fixed", reason="x",
                    locked=locked, runner=Mock(),
                )
            self.assertIsNone(handoff)
            self.assertIsNone(how)
            self.assertEqual(outcome.action, "kept-locked")
            mark.assert_not_called()

    def test_foreign_handoff_is_not_ours(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            handoffs = root / ".claude/worktrees/agent-test/tmp/_handoff"
            handoffs.mkdir(parents=True)
            (handoffs / "verification-author--issue-354.yaml").write_text("keep")
            entry = {
                "agent_type": "issue-implementer", "issue": 354,
                "worktree_path": ".claude/worktrees/agent-test",
            }
            self.assertEqual(_own_handoff(root, entry), (None, "empty"))

    def test_missing_branch_refuses_discard_without_git(self):
        entry = {"worktree_path": ".claude/worktrees/agent-test"}
        with patch("gitgate.worktree_sweep_discard._is_worktree_clean") as clean:
            allowed, why = _is_discardable(".", entry, runner=Mock())
        self.assertFalse(allowed)
        self.assertIn("branch_name", why)
        clean.assert_not_called()


class SweepG03IsolationTests(unittest.TestCase):
    def test_failure_is_reported_and_later_entries_still_processed(self):
        entries = [
            {"entry_id": "one", "worktree_path": "first", "status": "running"},
            {"entry_id": "two", "worktree_path": "second", "status": "running"},
        ]
        def process(_repo, entry, **kwargs):
            if entry["entry_id"] == "one":
                raise RuntimeError("unexpected")
            return SweepEntryOutcome("two", "second", "release-pending", "retained")
        with patch("gitgate.worktree_sweep._entries", return_value=entries):
            with patch("gitgate.worktree_sweep._locked_worktree_paths", return_value=set()):
                results = run_sweep(".", now="fixed", reason="retry",
                                    no_live_dispatch=True, runner=Mock(),
                                    sweep_one=process)
                repeated = run_sweep(".", now="fixed", reason="retry",
                                     no_live_dispatch=True, runner=Mock(),
                                     sweep_one=process)
        self.assertEqual(
            [(item.entry_id, item.action) for item in results],
            [("one", "kept-error"), ("two", "release-pending")],
        )
        self.assertEqual(results, repeated)

    def test_unreadable_lock_observation_fails_closed(self):
        entries = [{"entry_id": "one", "worktree_path": "first", "status": "running"}]
        process = Mock()
        with patch("gitgate.worktree_sweep._entries", return_value=entries):
            with patch("gitgate.worktree_sweep._locked_worktree_paths",
                       side_effect=RuntimeError("git unavailable")):
                result = run_sweep(".", now="fixed", reason="x",
                                   no_live_dispatch=True, runner=Mock(),
                                   sweep_one=process)
        self.assertEqual(result, [])
        process.assert_not_called()
