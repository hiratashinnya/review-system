"""Issue #655 AC: legacy PR re-review shares categorized untracked diagnostics."""
import tempfile
import unittest
from pathlib import Path

from codex_worktree_exec.untracked_recovery import main as recover
from issue_start.gate_support import IssueStartError
from tests.unit.legacy_pr_support import LegacyPrFixture


class PrRereviewRecoveryTests(unittest.TestCase):
    def test_legacy_pr_rereview_detects_and_recovers_generated_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = LegacyPrFixture(temporary)
            fixture.git("checkout", "-q", "main")
            (fixture.root / ".coverage").write_bytes(b"dummy not production coverage")
            (fixture.root / "htmlcov").mkdir()
            (fixture.root / "htmlcov" / "index.html").write_text("dummy")
            with self.assertRaises(IssueStartError) as raised:
                fixture.parse()
            self.assertEqual(raised.exception.reason, "ISSUE_START_PR_REREVIEW_INVALID")
            self.assertIn("coverage_output count=2", raised.exception.detail)
            out = Path(temporary) / "safe-quarantine"
            out.mkdir()
            self.assertEqual(recover(["--worktree", str(fixture.root),
                                      "--quarantine-parent", str(out), "--apply"]), 0)
            self.assertEqual(len(list(out.glob(
                "review-system-quarantine-*/htmlcov/index.html"))), 1)
            self.assertIsNotNone(fixture.parse())
