"""G-04 golden stdout/stderr, exit and side-effect calls for worktree verbs."""
import io
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from gitgate import cli


class WorktreeCliG04Contracts(unittest.TestCase):
    def setUp(self):
        self.root = Path("/synthetic/repository")
        self.now = object()

    def _invoke(self, verb, parser, request, operation, result):
        with patch("gitgate.cli._now", return_value=self.now), \
             patch("gitgate.cli_worktree.default_repo_root", return_value=self.root), \
             patch(f"gitgate.cli_worktree.{parser}", return_value=request), \
             patch(f"gitgate.cli_worktree.{operation}", return_value=result) as run, \
             patch("sys.stderr", new_callable=io.StringIO) as stderr, \
             patch("sys.stdout", new_callable=io.StringIO) as stdout:
            rc = cli.main([verb])
        self.assertEqual(rc, 0)
        self.assertEqual(stdout.getvalue(), "")
        return run, stderr.getvalue()

    def test_release_stderr_and_exact_side_effect_arguments(self):
        req = SimpleNamespace(worktree_path=".claude/worktrees/agent-a",
                              entry_id="entry-a", force_uncollected=False, reason="done")
        result = SimpleNamespace(worktree_path=req.worktree_path, entry_id=req.entry_id,
                                 removed=True, status="released")
        run, err = self._invoke("worktree-release", "parse_worktree_release_args",
                                req, "worktree_release", result)
        run.assert_called_once_with(
            self.root, req.worktree_path, entry_id="entry-a",
            force_uncollected=False, reason="done", now=self.now)
        self.assertEqual(err, "gitgate: worktree-release .claude/worktrees/agent-a "
                         "entry=entry-a removed=yes status=released\n")

    def test_collect_stderr_and_exact_side_effect_arguments(self):
        req = SimpleNamespace(entry_id="entry-a", worktree_path=None,
                              handoff_path="handoff.md", into=None,
                              allow_missing_handoff=False, reason="done")
        result = SimpleNamespace(worktree_path=".claude/worktrees/agent-a",
                                 entry_id="entry-a", collected_to="collected/a",
                                 released=False)
        run, err = self._invoke("collect-worktree", "parse_collect_worktree_args",
                                req, "collect_worktree", result)
        run.assert_called_once_with(
            self.root, entry_id="entry-a", worktree_path=None,
            handoff_path="handoff.md", into=None,
            allow_missing_handoff=False, reason="done", now=self.now)
        self.assertEqual(err, "gitgate: collect-worktree .claude/worktrees/agent-a "
                         "entry=entry-a collected_to=collected/a released=no\n")

    def test_sweep_status_lines_summary_and_no_live_dispatch(self):
        req = SimpleNamespace(reason="resume", no_live_dispatch=True)
        outcomes = [
            SimpleNamespace(worktree_path="agent-a", entry_id="a",
                            action="released", detail=None),
            SimpleNamespace(worktree_path="agent-b", entry_id="b",
                            action="kept-stale", detail="dirty"),
        ]
        run, err = self._invoke("worktree-sweep-abandoned", "parse_worktree_sweep_args",
                                req, "sweep_abandoned_running", outcomes)
        run.assert_called_once_with(
            self.root, now=self.now, reason="resume", no_live_dispatch=True)
        self.assertEqual(err, "gitgate: worktree-sweep-abandoned agent-a "
                         "entry=a action=released\n"
                         "gitgate: worktree-sweep-abandoned agent-b "
                         "entry=b action=kept-stale detail=dirty\n"
                         "gitgate: worktree-sweep-abandoned candidates=2 released=1\n")

    def test_forget_only_updates_state_and_emits_contract_message(self):
        req = SimpleNamespace(entry_id="entry-a", reason="unrecoverable")
        run, err = self._invoke("worktree-forget", "parse_worktree_forget_args",
                                req, "worktree_forget", {"status": "abandoned"})
        run.assert_called_once_with(self.root, "entry-a",
                                    reason="unrecoverable", now=self.now)
        self.assertEqual(err, "gitgate: worktree-forget entry-a status=abandoned "
                         "(worktree は削除していない)\n")


if __name__ == "__main__":
    unittest.main()
